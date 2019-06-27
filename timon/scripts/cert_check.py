#!/usr/bin/env python

# #############################################################################
"""
    Summary: probe to check cert validity
"""
# #############################################################################
from __future__ import absolute_import
from __future__ import print_function


import datetime
import socket
import ssl


import click
from dateutil import parser
import pytz


helptxt = ("""
checks validity of ssl cert for a given server

HOSTPORT is either a host name or an ip addresse optionally followed
by ':' and a port number.
""")


def get_cert_status(hostname, port, servername):
    sock = socket.create_connection((hostname, port), timeout=5)
    ctx = ssl.create_default_context()

    with ctx.wrap_socket(sock, server_hostname=servername) as sslsock:
        cert = sslsock.getpeercert()
    not_bef = cert['notBefore']
    not_aft = cert['notAfter']
    not_bef = parser.parse(not_bef)
    not_aft = parser.parse(not_aft)

    now = datetime.datetime.utcnow()
    now = now.replace(tzinfo=pytz.utc)
    # print(not_bef, not_aft, now)

    if now < not_bef:
        return "ERROR", "cert in the future"

    still_valid = (not_aft - now).days
    # print(still_valid)

    if still_valid <= 0:
        return "ERROR", "cert expired"
    elif still_valid <= 20:
        return "WARNING", "cert expires soon (%d<20 days)" % still_valid

    return "OK", "cert valid for %d days" % still_valid


@click.command(help=helptxt)
@click.argument(
    "hostport",
    )
@click.option(
    "-s", "--servername",
    help="servername in case it differs from HOSTPORT",
    )
def main(hostport, servername=None):
    hostname, port = (hostport + ":443").split(":", 2)[:2]
    port = int(port)
    servername = hostname if not servername else servername
    # print(repr(hostname), repr(port), repr(servername))

    status, comment = get_cert_status(hostname, port, servername)
    print(status, comment)

    # cert = ssl.DER_cert_to_PEM_cert(der_cert)
    # print(cert)


if __name__ == "__main__":
    main()
