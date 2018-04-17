#!/usr/bin/env python

import json
import requests
import sys

from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


from . import flags  # noqa
#from .flags import FLAG_MAP  # noqa


def http_json(url, timeout=10, verify_ssl=True, cert=None):
    result = dict(
        exit_code=flags.FLAG_UNKNOWN,
        status="unknown",
        response={},
        reason=None,
        )
    # error = False
    # error_msg = ""
    try:
        resp = requests.get(url, timeout=10, verify=verify_ssl, cert=cert)
    except Exception as exc:
        result['reason'] = repr(exc)
        return result
    s_code = resp.status_code
    result['status'] = s_code
    if s_code == 200:
        try:
            result['response'] = resp.json()
            result['exit_code'] = flags.FLAG_OK
        except Exception as exc:
            result['reason'] = repr(exc)

    # could add code here, that adapts exit_code depending on
    # json response and the --ok-rule / --warning-rule / --error-rule flags
    return result


def mk_parser():
    import argparse
    description = "checks status via http / json"
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
    # can be implemented lateron if needed
    # parser.add_argument("--ok-rule",
    #     default=None,
    #     help="rule of type <field_name>:regex to indicate OK state. "
    #          "default= %(default)r"),
    # parser.add_argument("--warn-rule",
    #     default=None,
    #     help="rule of type <field_name>:regex to indicate OK state. "
    #          "default= %(default)r"),
    # parser.add_argument("--error-rule",
    #     default=None,
    #     help="rule of type <field_name>:regex to indicate OK state. "
    #          "default= %(default)r"),
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

    # error = False
    # error_msg = ""
    # status = "UNKNOWN"
    if options is None:
        result = http_json(host_url, timeout=10)
    else:
        verify_ssl = options.verify_ssl[0].lower() in "ty1"
        if verify_ssl:
            cert = (options.cert, options.key)
        else:
            cert = None
        result = http_json(host_url, timeout=10,
                           verify_ssl=verify_ssl, cert=cert)

    print(json.dumps(result, indent=1))
    exit(result['exit_code'])


if __name__ == "__main__":
    main()
