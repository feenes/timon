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
"""
# #############################################################################
import re
import socket
import sys

import click
from OpenSSL import SSL

from timon.conf.flags import FLAG_ERROR_STR
from timon.conf.flags import FLAG_MAP
from timon.conf.flags import FLAG_OK_STR
from timon.conf.flags import FLAG_UNKNOWN_STR

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
    # at the moment we have to **NOT** use TLS1.3 in order to get
    # list of CAs
    ctx.set_options(SSL.OP_NO_TLSv1_3)
    # I don't know what to do as soon as we have the first server that
    # does no more support protocols < TLSv1.3
    # TODO: re-check https://stackoverflow.com/a/69444406/858675
    # Perhaps this will also work with TLS 1.3
    sock = SSL.Connection(
        ctx, socket.socket(socket.AF_INET, socket.SOCK_STREAM))
    sock.set_tlsext_host_name(hostname.encode("utf-8"))
    sock.connect((hostname, port))
    sock.do_handshake()
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
