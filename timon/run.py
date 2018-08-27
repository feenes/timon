#!/usr/bin/env python
"""
#############################################################################
Copyright : (C) 2017 by Teledomic.eu All rights reserved

Name:         timon.run

Description:  main tmon runner

#############################################################################
"""

from __future__ import absolute_import, print_function

import asyncio
import logging
import os
import sys
import time
# import signal


import timon.config

from timon.config import get_config
from timon.probe_if import mk_probe


logger = logging.getLogger(__name__)


@asyncio.coroutine
def ask_exit(loop, signame):
    """
    at the moment not used.
    This code is an attempt to help performing a
    clean shutdown
    """
    print("got signal %s: will exit" % signame)
    yield from asyncio.sleep(1.0)
    loop.stop()


def exec_shell_loop(args, delay=60):
    """
    runs timon as a shell_loop
    The shell loop is a minimalis shell, that sleeps and executes
    timon every dly seconds.
    If even this shell loop consumes too much memory, then crontab
    can be used to call timon regularly.
    """
    # strip off -s / --shell-loop args
    if '-s' in args:
        args.remove('-s')
    if '--shell-loop' in args:
        args.remove('--shell-loop')

    if delay == "auto":
        delay = 60
    else:
        delay = int(delay)

    mydir = os.path.dirname(__file__)
    shell_cmd = os.path.join(mydir, 'data', 'scripts', 'timonloop.sh')

    pydir = os.path.realpath(os.path.dirname(sys.executable))
    os.environ['PATH'] = os.environ['PATH'] + os.pathsep + os.path.join(pydir)
    # call execl: This will never return
    os.execl(shell_cmd, shell_cmd, str(delay), *args)


async def run_once(options, loop=None, first=False, cfg=None):
    """ runs one probe iteration
        returns:
            (t_next, notifiers, loop)
            t_next: in how many seconds the next probe should be fired
            notifiers: list of notifiers, that were started
            loop: loop in which notofiers were started
    """

    t0 = time.time()  # now
    # print("OPTS:", options)
    cfg = cfg if cfg else get_config(options=options)
    # print("CFG: %r" % cfg)
    # state = cfg.get_state()
    # print("state", state)
    queue = cfg.get_queue()
    print("IQ", queue)
    if first:
        cfg.refresh_queue()
        print("IR")

        # get all queue entries less than a certain time stamp (dflt=now)

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
    else:
        probes = queue.get_probes(force=options.force)
        probes = list(probes)
        logger.debug("probes: %s", repr(probes))

    from timon.runner import Runner
    runner = Runner(probes, queue, loop=loop)
    t_next = await runner.run(force=options.probe)

    cfg.save_state()

    t = time.time()
    t_delta_next = max(t_next - t, 1)

    if runner.notifiers:
        return t_delta_next, runner.loop, runner.notifiers

    if not loop:
        runner.close()

    return max(t_next - t, 1), None, []


async def run_loop(options, cfg, run_once_func=run_once, t00=None):
    """
    the async application loop
    """
    loop = asyncio.get_event_loop()
    first = True
    dly, rslt_loop, notifiers = None, None, None
    while True:
        # TODO: clean all_notifiers
        # print("OPTIONS:\n", options)
        t0 = time.time()  # now
        print("RO @", t0 - t00)
        dly, rslt_loop, notifiers = await run_once(
                options, loop=loop, cfg=cfg, first=first)
        print("end of run_once")
        first = False
        t1 = time.time()  # now
        print("RODONE @", t1 - t00)
        if not options.loop:
            break
        dly = dly - (t1 - t0)
        print("DLY =", dly)
        if dly > 0:
            print("sleep %f" % dly)
            await asyncio.sleep(dly)
    if notifiers:
        for notifier in notifiers:
            print("wait for notifier", notifier._coro)
            await notifier
            print("notifier done")
    return dly, rslt_loop, notifiers


def run(options):
    """
    starting point for a run
    """
    t00 = time.time()  # now
    # print("OPTIONS:\n", options)
    if options.shell_loop:
        exec_shell_loop(sys.argv[1:], options.loop_delay)
        return  # just to make it more obvious. previous line never returns

    cfg = timon.config.get_config(options=options)

    use_trio = cfg.get_plugin_param(
        'trio.enabled', default=False)
    if use_trio:
        print("load trio plugin")
        from timon.plugins.trio import run as run_trio
        return run_trio(options, cfg, run_once, t00, run_loop)

    if options.loop:
        # if we run in loop mode we must also see how to handle HUP signals
        # or force request for specific nodes via the so far not implemented
        # web API.

        use_aiomonitor = cfg.get_plugin_param(
            'aiomonitor.enabled', default=False)
        print("With loop option (trio=%r, aiomon=%r)" %
              (use_trio, use_aiomonitor))

        loop = asyncio.get_event_loop()

        if use_aiomonitor:
            import aiomonitor
            time.sleep(1)
            aiomonitor.start_monitor(loop=loop)

        # TODO: Read how exactly signal handlers are working
        # print("Will install signal handlers")
        # for signame in ('SIGINT', 'SIGTERM'):
        #     loop.add_signal_handler(
        #         getattr(signal, signame),
        #         lambda: asyncio.ensure_future(
        #             asyncio.gather(ask_exit(loop, signame))))
    else:
        print("Without loop option")
        loop = asyncio.get_event_loop()

    dly, rslt_loop, notifiers = loop.run_until_complete(
        run_loop(options, cfg, run_once, t00=t00))

    # In run once mode we have to wait till notifiers finished.
    # run loop till notifiers finished
