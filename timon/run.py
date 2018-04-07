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
import signal
import asyncio

from timon.config import get_config
from timon.probe_if import mk_probe


logger = logging.getLogger(__name__)

@asyncio.coroutine
def ask_exit(loop, signame):
    print("got signal %s: will exit" % signame)
    yield from asyncio.sleep(1.0)
    loop.stop()


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

    mydir  = os.path.dirname(__file__)
    shell_cmd = os.path.join(mydir, 'data', 'scripts', 'timonloop.sh')

    pydir = os.path.realpath(os.path.dirname(sys.executable))
    os.environ['PATH'] = os.environ['PATH'] + os.pathsep + os.path.join(pydir)
    os.execl(shell_cmd, shell_cmd, str(delay), *args )


def run_once(options, loop=None, first=False):
    """ runs one probe iteration """

    t0 = time.time() # now
    #print("OPTS:", options)
    cfg = get_config(options=options)
    #print("CFG: %r" % cfg)
    state = cfg.get_state()
    #print("state", state)
    queue = cfg.get_queue()
    print("IQ", queue)
    if first:
        cfg.refresh_queue()
        print("IR")

    if options.force:
        pass
    else:
        # get all queue entries less than a certain time stamp (dflt=now)
        probes = queue.get_probes()

    print("probes: %r" % probes)

    from timon.runner import Runner

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
    runner = Runner(probes, queue, loop=loop)
    t_next = runner.run()
    if not loop:
        runner.close()

    cfg.save_state()
    t = time.time()

    return max(t_next -t, 1)

    

    
def run(options):
    t00 = time.time() # now
    #print("OPTIONS:\n", options)
    if options.shell_loop:
        exec_shell_loop(sys.argv[1:], options.loop_delay)
        return # just to make it more obvious. In fact previous line never returns

    
    if options.loop:
        print("With loop option")
        loop = asyncio.get_event_loop() 
        print("Will install signal handlers")
        for signame in ('SIGINT', 'SIGTERM'):
            loop.add_signal_handler(getattr(signal, signame),
                lambda: asyncio.ensure_future(ask_exit(loop, signame)))
    else:
        print("Without loop option")
        loop = None

    first = True
    while True:
        #print("OPTIONS:\n", options)
        t0 = time.time() # now
        print("RO @", t0 - t00)
        dly = run_once(options, loop=loop, first=first)
        print("end of run_once")
        first = False
        #if loop:
        #    pending = asyncio.Task.all_tasks()
        #    loop.run_until_complete(asyncio.gather(*pending))
        t1 = time.time() # now
        print("RODONE @", t1 - t00)
        if not options.loop:
            break
        dly = dly - (t1 - t0)
        print("DLY =", dly)
        if dly > 0:
            print("sleep %f" % dly)
            loop.run_until_complete(asyncio.sleep(dly))

