#!/usr/bin/env python

# #############################################################################
"""
    Summary: probe to check whether an ssl server accepts certs signed by a
             given CA is acceptable for client certs
"""
# #############################################################################
import re
import socket
import sys

import click

from timon.scripts.flags import FLAG_ERROR_STR
from timon.scripts.flags import FLAG_MAP
from timon.scripts.flags import FLAG_OK_STR
from timon.scripts.flags import FLAG_UNKNOWN_STR

from OpenSSL import SSL

helptxt = ("""
checks whether client certs signed by a given CA will be accepted by a server

HOSTPORT is either a host name or an ip address optionally followed
by ':' and a port number.

CAREX is a regular expression to match a CA:
example:  C=FR/O=myorg/CN=CACert1
""")


def get_client_cert_cas(hostname, port):
    """ fetch client ca list without calling a subprocess """
    ctx = SSL.Context(SSL.SSLv23_METHOD)
    sock = SSL.Connection(
        ctx, socket.socket(socket.AF_INET, socket.SOCK_STREAM))
    sock.set_tlsext_host_name(hostname.encode("utf-8"))
    sock.connect((hostname, port))
    # TODO: just send one byte. perhaps there's a better way
    # to trigger fetching the ca_list?
    sock.send(b"G")
    rslt = []
    for ca in sock.get_client_ca_list():
        # TODO: convert each X509Name object to a string.
        # probably this can be done better
        items = (b"%s=%s" % (name, val) for (name, val) in ca.get_components())
        rslt.append("/".join(item.decode("utf-8") for item in items))
    return rslt


@click.command(help=helptxt)
@click.argument("hostport")
@click.argument("carex")
def main(hostport, carex):
    if ":" in hostport:
        hostname, port_str = hostport.split(":")
        port = int(port_str)
    else:
        hostname = hostport
        port = 443
    status = FLAG_UNKNOWN_STR
    try:
        rslt = get_client_cert_cas(hostname, port)
    except Exception as exc:
        print(status, str(exc))
        raise

    carex = re.compile(carex)
    status = FLAG_ERROR_STR
    found = []
    for castr in rslt:
        # print(castr, file=sys.stderr)
        if carex.search(castr):
            found.append(castr)
            status = FLAG_OK_STR
            break
    msg = (" ".join(found)) or "-"
    print(status, msg)
    sys.exit(FLAG_MAP[status])


if __name__ == "__main__":
    main()
