#!/usr/bin/env python

import os
import sys
import time
import requests

from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


from . import flags
from .flags import FLAG_MAP

def isup(url, timeout=10, verify_ssl=True):
    error = False
    error_msg = ""
    try:
        resp = requests.get(url, timeout=10, verify=verify_ssl)
    except Exception as exc:
        error = True
        error_msg = repr(exc)
    if error:
        status = "ERROR"
        print(status, error_msg)
    else:
        s_code = resp.status_code
        status = "OK" if s_code in [200] else "ERROR"
        print(status, resp.status_code)
    return status


def mk_parser():
    import argparse
    description = "checks whether a web server is up"
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--verify_ssl",
            help="True to verify SSL. False to net set SSL (default=True)")
    parser.add_argument("host_url",
            help="host's url")
    return parser


def main():
    args = sys.argv[1:]
    if len(args) > 1 or "-h" in args or "--help" in args:
        parser = mk_parser()
        options = parser.parse_args(args)
        host_url = options.host_url
    else:
        options = None
        host_url = args[0]

    error = False
    error_msg = ""
    status = "UNKNOWN"
    if options is None:
        status = isup(host_url, timeout=10)
    else:
        verify_ssl = options.verify_ssl[0].lower() in "ty1"
        status = isup(host_url, timeout=10, verify_ssl=verify_ssl)

    if error:
        status = "ERROR"
        print(status, error_msg)
    exit(FLAG_MAP[status])

        
        

if __name__ == "__main__":
    main()
