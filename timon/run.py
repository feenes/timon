#!/usr/bin/env python
"""
#############################################################################
Copyright : (C) 2017 by Teledomic.eu All rights reserved

Name:         timon.run

Description:  main tmon runner

#############################################################################
"""

from __future__ import absolute_import, print_function

import os, sys
import time
import logging

from timon.config import get_config
from timon.probe_if import mk_probe


logger = logging.getLogger(__name__)

def exec_shell_loop(args, delay=60):
    """ runs timon as a shell_loop """
    # strip off -s / --shell-loop args
    if '-s' in args:
        args.remove('-s')
    if '--shell-loop' in args:
        args.remove('--shell-loop')

    if delay == "auto":
        delay = 60
    else:
        delay = int(delay)

    shell_cmd = os.path.join(os.path.dirname(__file__), 'data', 'scripts',
            'timonloop.sh')
    os.execl(shell_cmd, shell_cmd, str(delay), *args )


def run(options):
    # IMPLEMENT PARAMS/OPTIONS or remove doc string
    """ runs timon
        :param config: tmon config
        :param init: if True all probes will fire
    """
    print("run tmon")
    print(options)
    if options.shell_loop:
        exec_shell_loop(sys.argv[1:], options.loop_delay)

    t0 = time.time()
    #print("OPTS:", options)
    cfg = get_config(options=options)
    #print("CFG: %r" % cfg)
    state = cfg.get_state()
    #print("state", state)
    queue = cfg.get_queue()
    print("IQ", queue)
    cfg.refresh_queue() # add any not refreshed entries to queue


    #print("IR")
    from .runner import Runner

    # get all queue entries less than a certain time stamp (dflt=now)
    probes = queue.get_probes()

    if options.probe:
        to_call = set(options.probe)
        probes = []
        print("TO CALL", to_call)
        for prb in cfg.get_probes():
            if prb['name'] not in to_call:
                continue
            prb_dict = dict(
                t_next=t0 - 1,
                interval=100,
                failinterval=100,
                done_cb=None,
                )
            prb_dict.update(prb)
            print("prb", prb)
            prb = mk_probe(prb['cls'], **prb_dict)
            print("prb", prb)
            probes.append(prb)
        queue = None
    runner = Runner(probes, queue)
    runner.run()
    runner.close()

    cfg.save_state()
    t = time.time()
    print("t_tot =%.3f" % (t-t0))
    print("IQ", queue)
    
