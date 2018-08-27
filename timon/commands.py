#!/usr/bin/env python
"""
#############################################################################
Copyright : (C) 2017 by Teledomic.eu All rights reserved

Name       : timon.commands
Description : cli entry for timon

entry point for timon command line tool
#############################################################################
"""

from __future__ import absolute_import, print_function

# -----------------------------------------------------------------------------
#   Imports
# -----------------------------------------------------------------------------
import argparse
import os
import sys

# import these as early as possible to be sure logging is configured
# before any loggers are created.
# This breaks my default rule to import custom modules before
# built in / pypi modules
import mytb.logging.config


force_config = os.path.basename(sys.argv[0]) in ['timon']
logger = mytb.logging.config.getLogger(__name__, force_config=force_config)


import mytb.argparse  # noqa


# -----------------------------------------------------------------------------
#   Globals
# -----------------------------------------------------------------------------
MYNAME = os.path.splitext(os.path.basename(__file__))[0]


def show_help(parser, full_help=False):
    """ shows help """
    print(parser.format_help())
    if not full_help:
        return
    subparsers_actions = [
        action for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)]
    for subparsers_action in subparsers_actions:
        # get all subparsers and print help
        for _choice, subparser in subparsers_action.choices.items():
            print("-" * 76)
            print(subparser.format_help())


def mk_parser():
    """ commandline parser """
    description = "cli entry for timon"
    workdir = "."

    parser = mytb.argparse.mk_parser(description=description)
    parser.set_defaults(func=None)

    # ######## common args
    parser.add_argument(
        '-d', '--dryrun',
        action='store_true', help="do dryrun only")
    parser.add_argument('-v', '--verbose', action='store_true', default=False)
    parser.add_argument(
        '-w', '--workdir', default=workdir,
        help="config file name. default: %(default)s")
    parser.add_argument(
        '--fname', default="timon.yaml",
        help="config file base name")
    parser.add_argument(
        '-C', '--compiled-config', default="timoncfg_state.json",
        help="compiled config file name relative to workdir. "
             "default: %(default)s")
    parser.add_argument(
        '-D', '--debug',
        action='store_true', help="enable debugging")

    subparsers = parser.add_subparsers(dest='command', help='sub-command help')

    # ######## help (full help)
    sub_prs = subparsers.add_parser('help', description='shows help message')
    sub_prs.set_defaults(
            func=lambda options: show_help(parser, options.full_help))
    sub_prs.add_argument(
            '-a', '-all', action='store_true',
            dest='full_help', help='shows full help')

    # ######## init
    sub_prs = subparsers.add_parser(
        'init', description='inits a timon project')
    sub_prs.set_defaults(func='timon.init.init')

    # ######## config
    sub_prs = subparsers.add_parser(
        'config', description='applies/updates configuration')
    sub_prs.set_defaults(func='timon.configure.apply_config')
    sub_prs.add_argument(
            '-f', '--fname', default="timon.yaml",
            help="name of config file (relative path to workdir)")
    sub_prs.add_argument(
            '-c', '--check', action='store_true',
            help="checks config consistency")

    # ############ run
    sub_prs = subparsers.add_parser('run', description='runs tmon')
    sub_prs.set_defaults(func='timon.run.run')
    sub_prs.add_argument(
            '-f', '--fname', default="timon.yaml",
            help="name of config file (relative path to workdir)")
    sub_prs.add_argument(
            '-F', '--force', action='store_true',
            help="force execution of probes even if not scheduled")
    sub_prs.add_argument(
            '-s', '--shell-loop', action='store_true',
            help="runs a shell loop")
    sub_prs.add_argument(
            '-l', '--loop', action='store_true',
            help="runs in loop mode")
    sub_prs.add_argument(
            '-d', '--loop-delay', default="auto",
            help="specifies loop delay")

    sub_prs.add_argument(
            '--statefile',
            help=('specific location for a state file'
                  'only used when creating initial conf')
            ),
    sub_prs.add_argument(
            'probe', nargs="*",
            help="probe_id(s) to execute")

    # ########### status
    sub_prs = subparsers.add_parser(
        'status',
        description='display timon status')
    sub_prs.set_defaults(func='timon.report_status.report_status')
    sub_prs.add_argument(
            '-a', '--active', action='store_true',
            help="shows only probes, that are still active")

    return parser


def get_options(args=None, get_parser=False):
    """ helper to get options """
    args = args if args else []
    parser = mk_parser()
    options = parser.parse_args(args)
    if not hasattr(options, 'statefile'):
        options.statefile = None
    return (options, parser) if get_parser else options


def main():
    """ the main function """
    args = sys.argv[1:]
    logger.info("started timon %r", args)
    options, parser = get_options(args, get_parser=True)
    func = options.func
    if func is None:  # argparse shows no help if no cmd given. so force it
        parser.print_help()
        sys.exit(0)

    if func:
        if not type(func) is str:
            func(options)
        else:
            from mytb.importlib import import_obj
            func = import_obj(func)
            if options.debug:
                try:
                    import ipdb as pdb
                except ImportError:
                    import pdb
                pdb.set_trace()
            func(options=options)


if __name__ == '__main__':
    main()
# -----------------------------------------------------------------------------
#   End of file
# -----------------------------------------------------------------------------
