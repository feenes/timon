#!/usr/bin/env python

# #############################################################################
"""
    Summary: probe to check whether an ssl server accepts certs signed by a
             given CA is acceptable for client certs
"""
# #############################################################################
import re
import os
import subprocess
import sys

import click

from timon.scripts.flags import FLAG_ERROR_STR
from timon.scripts.flags import FLAG_MAP
from timon.scripts.flags import FLAG_OK_STR
from timon.scripts.flags import FLAG_UNKNOWN_STR


helptxt = ("""
checks whether client certs signed by a given CA will be accepted by a server

HOSTPORT is either a host name or an ip address optionally followed
by ':' and a port number.

CAREX is a regular expression to match a CA:
example:  C=FR/O=myorg/CN=CACert1
""")


def get_client_cert_cas(hostname, port):
    """
    returns a list of CAs, for which client certs are accepted
    """

    cmd = [
        "openssl",
        "s_client",
        "-showcerts",
        "-servername",  hostname,
        "-connect",  hostname + ":" + str(port),
        ]

    stdin = open(os.devnull, "r")
    stderr = open(os.devnull, "w")

    output = subprocess.check_output(cmd, stdin=stdin, stderr=stderr)
    ca_signatures = []
    state = 0
    for line in output.decode().split("\n"):
        if state == 0:
            if line == "Acceptable client certificate CA names":
                state = 1
        elif state == 1:
            if line.startswith("Client Certificate Types:"):
                break
            ca_signatures.append(line)
    return ca_signatures


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
    for castr in rslt:
        # print(castr, file=sys.stderr)
        if carex.search(castr):
            status = FLAG_OK_STR
            break
    print(status)
    sys.exit(FLAG_MAP[status])


if __name__ == "__main__":
    main()
