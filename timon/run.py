#!/usr/bin/env python
"""
#############################################################################
Copyright : (C) 2017 by Teledomic.eu All rights reserved

Name:         timon.run

Description:  main tmon runner

#############################################################################
"""

import asyncio
import logging
import os
import sys
import time

import timon.config
from timon.config import get_config
from timon.plugins.trio import run as run_trio
from timon.probe_if import mk_probe

logger = logging.getLogger(__name__)


async def ask_exit(loop, signame):
    """
    at the moment not used.
    This code is an attempt to help performing a
    clean shutdown
    """
    print("got signal %s: will exit" % signame)
    await asyncio.sleep(1.0)
    loop.stop()


def exec_shell_loop(args, delay=60):
    """
    runs timon as a shell_loop
    The shell loop is a minimalist shell, that sleeps and executes
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
    # logger.debug("OPTS:%s", str(options))
    cfg = cfg if cfg else get_config(options=options)
    # logger.debug("CFG: %r", str(cfg))
    # state = cfg.get_state()
    # print("state", state)
    queue = cfg.get_queue()
    logger.debug("IQ %s", str(queue))
    if first:
        cfg.refresh_queue()
        logger.debug("IR")

        # get all queue entries less than a certain time stamp (dflt=now)

    if options.probe:
        to_call = set(options.probe)
        probes = []
        logger.debug("TO CALL %s", str(to_call))
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
            logger.debug("prb %s", str(prb))
            prb = mk_probe(prb['cls'], **prb_dict)
            logger.debug("prb %s", str(prb))
            probes.append(prb)
        queue = None
    else:
        logger.debug("pregetp (force=%s)", options.force)
        probes = queue.get_probes(force=options.force)
        probes = list(probes)
        logger.debug("%d probes: %s", len(probes), repr(probes))

    from timon.runner import Runner
    runner = Runner(probes, queue, loop=loop)
    t_next = await runner.run(force=options.probe)

    cfg.save_state()

    t = time.time()
    t_delta_next = max(t_next - t, 0)

    if runner.notifier_objs:
        for notifier in runner.notifier_objs:
            task = runner.loop.create_task(notifier.notify())
            runner.notifiers.append(task)
        return t_delta_next, runner.loop, runner.notifiers

    if not loop:
        runner.close()

    return max(t_next - t, 0), None, []


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
        logger.debug("RO @%7.3f", t0 - t00)
        dly, rslt_loop, notifiers = await run_once(
                options, loop=loop, cfg=cfg, first=first)
        logger.debug("end of run_once")
        first = False
        t1 = time.time()  # now
        logger.debug("RODONE @%7.3f", t1 - t00)
        if not options.loop:
            break
        dly = dly - (t1 - t0)
        logger.debug("DLY = %7.3f", dly)
        if dly > 0:
            logger.debug("sleep %f", dly)
            await asyncio.sleep(dly)
    if notifiers:
        for notifier in notifiers:
            logger.debug("wait for notifier %s", str(notifier._coro))
            await notifier
            logger.debug("notifier done")
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

    return run_trio(options, cfg, run_once, t00, run_loop)
