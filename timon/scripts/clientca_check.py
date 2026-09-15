#!/usr/bin/env python

# #############################################################################
# Copyright : (C) 2023 by MHComm. All rights reserved
#
# __author__ = "Quentin Laymajoux"
# __email__ = "info@mhcomm.fr"
#
# Name       : timon.scripts.clientca_check
"""
Summary: probe to check whether an ssl server accepts certs signed by a
        given CA

This is the python equivalent of looking at the 'Acceptable client
certificate CA names' section of

    timeout 2 openssl s_client -showcerts \
        -connect ${hostaddr:-$host}:${port:-443} -servername ${host:-$hostaddr}

i.e. connect, let the server tell us which client CAs it accepts, keep the
connection open for a moment in case the request comes late, and match the
announced CAs against a regular expression.

timon starts this script as a subprocess and parses the merged stdout /
stderr positionally (first word = status flag), so it must print exactly
one line and must never let a traceback or a warning escape.
"""
# #############################################################################
import argparse
import collections
import ipaddress
import logging
import re
import select
import socket
import sys
import time
import warnings

# our stderr is merged into our stdout by the calling probe, which parses
# the first word of it as status flag. A deprecation warning of one of the
# imports below would therefore be mistaken for this probe's result.
warnings.simplefilter("ignore")

from OpenSSL import SSL  # noqa: E402

from timon.conf.flags import FLAG_ERROR_STR  # noqa: E402
from timon.conf.flags import FLAG_MAP  # noqa: E402
from timon.conf.flags import FLAG_OK_STR  # noqa: E402
from timon.conf.flags import FLAG_UNKNOWN_STR  # noqa: E402
from timon.conf.flags import FLAG_WARNING_STR  # noqa: E402

logger = logging.getLogger(__name__)

DEFAULT_PORT = 443
DEFAULT_TIMEOUT = 20
# how long to keep listening for a late CertificateRequest.
# This is the 'timeout 2' of the openssl s_client command above.
DEFAULT_LINGER = 2

helptxt = ("""
checks whether client certs signed by a given CA will be accepted by a server

HOSTPORT is either a host name or an ip address optionally followed
by ':' and a port number. IPv6 addresses shall be bracketed ('[::1]:443').

CAREX is a regular expression to match a CA:
example:  C=FR/O=myorg/CN=CACert1

Status is OK if at least one announced CA matches CAREX, ERROR if the
server asks for no client cert at all or announces only non matching CAs,
and UNKNOWN if the server could not be probed at all.

A server may also ask for a client cert without naming any CA. It then
accepts certs of any CA (which is why a browser offers all of its client
certs) and there is nothing to match CAREX against, so the status is
WARNING. Sending a cert is the only way to check such a server.
""")


# what a server told us about the client certs it wants
# :param version: name of the negotiated tls version
# :param requested: whether the server sent a CertificateRequest at all
# :param cas: the CAs it named in there. May be empty although it asked
CAInfo = collections.namedtuple("CAInfo", "version requested cas")


def parse_hostport(hostport, default_port=DEFAULT_PORT):
    """
    splits a host / port string into its two components

    accepts 'host', 'host:port', '::1', '[::1]' and '[::1]:443'
    """
    hostport = hostport.strip()
    if hostport.startswith("["):  # bracketed ipv6 address (rfc 3986)
        host, _, rest = hostport[1:].partition("]")
        if rest and not rest.startswith(":"):
            raise ValueError(f"malformed host/port {hostport!r}")
        port_str = rest[1:]
    elif hostport.count(":") > 1:  # unbracketed ipv6 address -> no port
        host, port_str = hostport, ""
    else:
        host, _, port_str = hostport.partition(":")

    if not host:
        raise ValueError(f"no host name in {hostport!r}")
    if not port_str:
        return host, default_port
    if not port_str.isdigit() or not 0 < int(port_str) < 65536:
        raise ValueError(f"bad port {port_str!r} in {hostport!r}")
    return host, int(port_str)


def mk_sni_name(servername):
    """
    server name to announce via SNI or None if SNI shall be skipped

    like openssl s_client we send the host name, but never an ip address:
    rfc 6066 forbids those and some servers abort the handshake on them.
    """
    try:
        ipaddress.ip_address(servername)
        return None
    except ValueError:
        pass
    name = servername.rstrip(".")  # a trailing root dot is invalid in SNI
    try:
        return name.encode("idna")
    except UnicodeError:  # no valid idna name. let the server complain
        return name.encode("utf-8", "replace")


def x509name_to_str(name):
    """
    converts an X509Name to timon's CA notation

    e.g. 'C=FR/O=myorg/CN=CACert1'
    """
    return "/".join(
        "%s=%s" % (
            key.decode("utf-8", "replace"), val.decode("utf-8", "replace"))
        for key, val in name.get_components()
        )


def wait_for_io(conn, want_read, deadline):
    """ waits till conn is readable / writable, raises TimeoutError if not """
    timeout = deadline - time.monotonic()
    readers, writers = ([conn], []) if want_read else ([], [conn])
    if timeout <= 0 or not any(
            select.select(readers, writers, [], timeout)[:2]):
        raise TimeoutError("timeout during ssl handshake")


def do_handshake(conn, deadline):
    """
    performs the ssl handshake on a non blocking connection

    a non blocking socket is the only portable way to put an upper limit
    on the duration of a handshake. Without it a silent server makes this
    probe hang forever.
    """
    while True:
        try:
            conn.do_handshake()
            return
        except SSL.WantReadError:
            wait_for_io(conn, True, deadline)
        except SSL.WantWriteError:
            wait_for_io(conn, False, deadline)


def linger(conn, deadline):
    """
    keeps reading from an idle connection till deadline

    Some servers only ask for a client cert once they know what is being
    requested and send their CertificateRequest a little later (TLS <= 1.2
    renegotiation). openssl s_client sees those because it stays connected,
    so we do the same before concluding that no CA was announced.
    """
    while time.monotonic() < deadline:
        try:
            if not conn.recv(4096):
                return
        except (SSL.WantReadError, SSL.WantWriteError):
            try:
                wait_for_io(conn, conn.want_read(), deadline)
            except TimeoutError:
                return
        except (SSL.ZeroReturnError, SSL.Error, OSError):
            return


def mk_cert_request_watcher():
    """
    mk (callback, was_requested) watching for the server's CertificateRequest

    A server may ask for a client cert without naming a single CA, so the
    CA list alone cannot tell us whether it asked at all. openssl has no
    api exposing that, but it walks through a distinct handshake state
    when it reads the CertificateRequest, and the info callback sees it.

    Should openssl ever rename that state we simply stop distinguishing
    'asked for any CA' from 'did not ask', which is what we did before.
    """
    seen = []

    def info_callback(conn, where, ret):
        try:
            state = conn.get_state_string().decode("ascii", "replace")
        except Exception:  # never break a handshake over some diagnostics
            return
        if "certificate request" in state.lower():
            seen.append(state)

    return info_callback, seen


def get_client_cert_cas(
        hostname, port, deadline, servername=None, allow_tls13=True,
        linger_time=DEFAULT_LINGER):
    """
    fetch client ca list without calling a subprocess

    :param deadline: time.monotonic() value at which to give up
    :param servername: name to send via SNI (defaults to hostname)
    :param allow_tls13: whether TLS1.3 may be negotiated
    :param linger_time: seconds to wait for a late CertificateRequest
    :returns: a CAInfo
    """
    ctx = SSL.Context(SSL.TLS_CLIENT_METHOD)
    # we only want to know which client CAs the server announces.
    # Whether its own cert is trustworthy is the cert_check probe's job.
    ctx.set_verify(SSL.VERIFY_NONE)
    if not allow_tls13:
        ctx.set_options(SSL.OP_NO_TLSv1_3)
    info_callback, cert_requested = mk_cert_request_watcher()
    ctx.set_info_callback(info_callback)

    # create_connection resolves the name and copes with IPv4 and IPv6
    sock = socket.create_connection(
        (hostname, port), timeout=max(0.1, deadline - time.monotonic()))
    conn = SSL.Connection(ctx, sock)
    try:
        sock.setblocking(False)  # timeouts are enforced by do_handshake()
        sni_name = mk_sni_name(servername or hostname)
        if sni_name:
            conn.set_tlsext_host_name(sni_name)
        conn.set_connect_state()
        do_handshake(conn, deadline)
        version = conn.get_protocol_version_name()
        cas = conn.get_client_ca_list()
        if not cas and linger_time > 0:
            linger(conn, min(deadline, time.monotonic() + linger_time))
            cas = conn.get_client_ca_list()
        return CAInfo(
            version=version,
            # a named CA implies a CertificateRequest, so the watcher only
            # matters for servers asking without naming any
            requested=bool(cas) or bool(cert_requested),
            cas=[x509name_to_str(ca) for ca in cas],
            )
    finally:
        # be nice to the server and never leak the socket
        try:
            conn.shutdown()
        except Exception:
            pass
        conn.close()


def get_client_ca_info(
        hostname, port, servername=None, timeout=DEFAULT_TIMEOUT,
        linger_time=DEFAULT_LINGER):
    """
    gets what an ssl server wants in terms of client certs

    The way a server announces its client CAs depends on the tls version:
    up to TLS1.2 they are sent in the CertificateRequest message, since
    TLS1.3 in its 'certificate_authorities' extension. Current openssl
    reports both through get_client_ca_list(), so - just like s_client -
    we start with a normal handshake and let the server pick a version.

    Should that name no CA at all we retry with TLS1.3 disabled, because
    - openssl builds older than 1.1.1 do not expose the TLS1.3 extension
    - a server may name its CAs in a TLS1.2 CertificateRequest only
    - a server that asks for the cert late can only do so by renegotiating,
      which does not exist in TLS1.3 (its post handshake auth is not
      reachable through pyopenssl)
    A server that only speaks TLS1.3 simply fails that second attempt and
    the result of the first one is kept.

    :returns: a CAInfo
    """
    deadline = time.monotonic() + timeout
    # keep half of the budget for a potential second attempt
    info = get_client_cert_cas(
        hostname, port, deadline - timeout / 2, servername=servername,
        linger_time=linger_time)
    if info.cas or info.version != "TLSv1.3":
        return info

    logger.debug(
        "%s:%s named no client CA via %s. retrying without TLS1.3",
        hostname, port, info.version)
    try:
        info2 = get_client_cert_cas(
            hostname, port, deadline, servername=servername,
            allow_tls13=False, linger_time=linger_time)
    except Exception as exc:
        # most probably a TLS1.3 only server, so trust the first attempt
        logger.debug(
            "TLS1.2 fallback for %s:%s failed: %r", hostname, port, exc)
        return info
    # keep whatever the two attempts found out together
    return CAInfo(
        version=info2.version,
        requested=info.requested or info2.requested,
        cas=info2.cas or info.cas,
        )


def get_ca_status(
        hostname, port, carex, servername=None, timeout=DEFAULT_TIMEOUT,
        linger_time=DEFAULT_LINGER):
    """
    :param carex: compiled regex a CA string must match
    :returns: (status flag string, message)
    """
    info = get_client_ca_info(
        hostname, port, servername=servername, timeout=timeout,
        linger_time=linger_time)
    logger.debug("%s:%s -> %s", hostname, port, info)

    if not info.requested:
        return (
            FLAG_ERROR_STR,
            f"server asks for no client cert ({info.version})")

    if not info.cas:
        # naming CAs is optional. A server asking without naming any takes
        # certs of whatever CA (which is why a browser then offers all of
        # its client certs), so there is nothing to match carex against.
        # Only sending a cert could tell us whether it is accepted.
        return (
            FLAG_WARNING_STR,
            f"server asks for a client cert but names no CA, "
            f"cannot check '{carex.pattern}' ({info.version})")

    found = [castr for castr in info.cas if carex.search(castr)]
    if not found:
        return (
            FLAG_ERROR_STR,
            f"no CA matching '{carex.pattern}' "
            f"in {len(info.cas)} named CAs ({info.version})")
    # CA names contain spaces, so they can't be separated by one
    return FLAG_OK_STR, "; ".join(found) + f" ({info.version})"


def mk_msg(msg):
    """ one line message, as the calling probe parses our output by line """
    return " ".join(str(msg).split()) or "-"


def positive_float(minimum):
    """ mk an argparse type checking that a float is >= minimum """
    def check(value):
        try:
            value = float(value)
        except ValueError:
            raise argparse.ArgumentTypeError(f"{value!r} is not a number")
        if value < minimum:
            raise argparse.ArgumentTypeError(f"{value} is smaller than "
                                             f"{minimum}")
        return value
    return check


class ProbeArgumentParser(argparse.ArgumentParser):
    """
    ArgumentParser reporting usage errors the way timon expects them

    argparse writes them to stderr and exits with 2, which happens to be
    timon's ERROR flag, so a typo in the probe's config would look like a
    failing server instead of a broken probe.
    """
    def error(self, message):
        print(FLAG_UNKNOWN_STR, mk_msg(f"bad arguments: {message}"),
              flush=True)
        sys.exit(FLAG_MAP[FLAG_UNKNOWN_STR])


def mk_parser():
    parser = ProbeArgumentParser(
        description=helptxt,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        )
    parser.add_argument(
        "-s", "--servername",
        help="name to send via SNI if it differs from HOSTPORT's host")
    parser.add_argument(
        "-t", "--timeout",
        type=positive_float(0.1),
        default=DEFAULT_TIMEOUT,
        help="overall time budget in seconds, half of it being reserved "
             "for the TLS1.2 fallback (default=%(default)s)")
    parser.add_argument(
        "-l", "--linger",
        dest="linger_time",
        metavar="LINGER",
        type=positive_float(0),
        default=DEFAULT_LINGER,
        help="seconds to wait for a late CertificateRequest, 0 to disable "
             "(default=%(default)s)")
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="log details to stderr. NOT to be used by the timon probe")
    parser.add_argument(
        "hostport",
        help="host name or ip address, optionally followed by ':' and a port")
    parser.add_argument(
        "carex",
        help="regular expression a CA string must match")
    return parser


def main():
    options = mk_parser().parse_args()
    if options.verbose:
        logging.basicConfig(level=logging.DEBUG, stream=sys.stderr)

    try:
        hostname, port = parse_hostport(options.hostport)
        status, msg = get_ca_status(
            hostname, port, re.compile(options.carex),
            servername=options.servername, timeout=options.timeout,
            linger_time=options.linger_time)
    except Exception as exc:
        # a traceback on stderr would be parsed as this probe's result by
        # the calling probe, so any error must be reported as a status line
        logger.debug("probing %s failed", options.hostport, exc_info=True)
        status, msg = FLAG_UNKNOWN_STR, repr(exc)

    print(status, mk_msg(msg), flush=True)
    sys.exit(FLAG_MAP[status])


if __name__ == "__main__":
    main()
