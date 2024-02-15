#!/usr/bin/env python

# #############################################################################
# Copyright : (C) 2023 by MHComm. All rights reserved
#
# __author__ = "Quentin Laymajoux"
# __email__ = "info@mhcomm.fr"
#
# Name       : timon.scripts.cert_check
"""
Summary      : probe to check cert validity

"""
# #############################################################################
import datetime
import logging
import ssl
import sys

import click
from cryptography import x509
from cryptography.hazmat.backends import default_backend

from timon.conf.flags import FLAG_ERROR
from timon.conf.flags import FLAG_ERROR_STR
from timon.conf.flags import FLAG_MAP
from timon.conf.flags import FLAG_OK_STR
from timon.conf.flags import FLAG_WARNING_STR

logger = logging.getLogger(__name__)

helptxt = ("""
checks validity of ssl cert for a given server

HOSTPORT is either a host name or an ip address optionally followed
by ':' and a port number.
""")


def get_cert_info(hostname, port, servername):
    """
    gets cert info from an ssl socket
    function can be mocked for testing
    """
    conn = ssl.create_connection((hostname, port))
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE  # accept self signed certs
    sock = context.wrap_socket(conn, server_hostname=hostname)
    cert = sock.getpeercert(True)
    cert = ssl.DER_cert_to_PEM_cert(cert)
    cert = cert.encode('utf-8')
    cert = x509.load_pem_x509_certificate(cert, default_backend())
    return cert


def get_cert_status(hostname, port, servername):
    cert = get_cert_info(hostname, port, servername)

    try:
        not_bef = cert.not_valid_before_utc
        not_aft = cert.not_valid_after_utc
    except AttributeError:
        # Workaround for criptography < 42.0
        not_bef = cert.not_valid_before
        not_aft = cert.not_valid_after

    # subject = cert.subject
    # cn = subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
    # print(cn)

    cert_duration = (not_aft - not_bef).days
    min_validity = 20 if cert_duration < 100 else 40

    now = datetime.datetime.utcnow()

    if now < not_bef:
        return FLAG_ERROR_STR, "cert in the future"

    still_valid = (not_aft - now).days
    # print(still_valid)

    if still_valid <= 0:
        return FLAG_ERROR_STR, "cert expired: %d days" % -still_valid

    # TODO: check that hostname matches CN or alt names
    if still_valid <= min_validity:
        msg = f"cert expires soon ({still_valid}<{min_validity} days)"
        return FLAG_WARNING_STR, msg

    return FLAG_OK_STR, "cert valid for %d days" % still_valid


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
        logger.warning(
            "%s: servername param still not fully supported", FLAG_ERROR_STR)
        exit(FLAG_ERROR)

    try:
        status, comment = get_cert_status(hostname, port, servername)
    except ssl.SSLError:
        status, comment = get_cert_status2(hostname, port, servername)

    print(status, comment)
    sys.exit(FLAG_MAP[status])


if __name__ == "__main__":
    main()
