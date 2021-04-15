#!/usr/bin/env python

import sys

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from requests.packages.urllib3.util.retry import Retry

from .flags import FLAG_MAP

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


RETRY_STRATEGY = Retry(
    total=3,
    backoff_factor=60,  # sleeps in s will be 30, 60, 120
    method_whitelist=["HEAD", "GET", "OPTIONS"]
)


def isup(url, timeout=30, verify_ssl=True, cert=None):
    error = False
    error_msg = ""
    adapter = HTTPAdapter(max_retries=RETRY_STRATEGY)
    http = requests.Session()
    http.mount("https://", adapter)
    http.mount("http://", adapter)
    try:
        resp = http.get(url, timeout=timeout, verify=verify_ssl, cert=cert)
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
    import argparse # noqa
    description = "checks whether a web server is up"
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
            "--verify_ssl",
            default="True",
            help="True to verify SSL. False to not check SSL (default=True)")
    parser.add_argument(
            "--key",
            help="file name of client cert's key")
    parser.add_argument(
            "--cert",
            help="file name of client cert")
    parser.add_argument(
            "host_url",
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
        status = isup(host_url, timeout=30)
    else:
        verify_ssl = options.verify_ssl[0].lower() in "ty1"
        if verify_ssl:
            cert = (options.cert, options.key)
        else:
            cert = None
        status = isup(host_url, timeout=30, verify_ssl=verify_ssl, cert=cert)

    if error:
        status = "ERROR"
        print(status, error_msg)
    exit(FLAG_MAP[status])


if __name__ == "__main__":
    main()
