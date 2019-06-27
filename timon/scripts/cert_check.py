#!/usr/bin/env python

# #############################################################################
"""
    Summary: probe to check cert validity
"""
# #############################################################################
from __future__ import absolute_import
from __future__ import print_function


import datetime
import ssl


import click

from cryptography import x509
from cryptography.hazmat.backends import default_backend
# from cryptography.x509.oid import NameOID


helptxt = ("""
checks validity of ssl cert for a given server

HOSTPORT is either a host name or an ip address optionally followed
by ':' and a port number.
""")


def get_cert_status(hostname, port, servername):

    conn = ssl.create_connection((hostname, port))
    context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    sock = context.wrap_socket(conn, server_hostname=hostname)
    cert = sock.getpeercert(True)
    cert = ssl.DER_cert_to_PEM_cert(cert)
    cert = cert.encode('utf-8')
    cert = x509.load_pem_x509_certificate(cert, default_backend())

    not_bef = cert.not_valid_before
    not_aft = cert.not_valid_after

    # subject = cert.subject
    # cn = subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
    # print(cn)

    now = datetime.datetime.utcnow()

    if now < not_bef:
        return "ERROR", "cert in the future"

    still_valid = (not_aft - now).days
    # print(still_valid)

    if still_valid <= 0:
        return "ERROR", "cert expired: %d days" % -still_valid

    # TODO: check that hostname matches CN or alt names
    if still_valid <= 20:
        return "WARNING", "cert expires soon (%d<20 days)" % still_valid

    return "OK", "cert valid for %d days" % still_valid


def get_cert_status2(hostname, port, servername):

    return "???", "not implemented"


@click.command(help=helptxt)
@click.argument(
    "hostport",
    )
# TODO: to be implemented for some boundary cases
# @click.option(
#     "-s", "--servername",
#     help="servername in case it differs from HOSTPORT",
#     )
def main(hostport, servername=None):
    hostname, port = (hostport + ":443").split(":", 2)[:2]
    port = int(port)
    servername = hostname if not servername else servername

    if (servername != hostname):
        print("ERROR: servername param still not fully supported")
        exit(1)

    try:
        status, comment = get_cert_status(hostname, port, servername)
    except ssl.SSLError:
        status, comment = get_cert_status2(hostname, port, servername)

    print(status, comment)


if __name__ == "__main__":
    main()
