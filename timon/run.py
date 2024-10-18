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
import signal
import sys
import time

import timon.conf.config
from timon.conf.config import get_config
from timon.conf.settings import PARANOIA_LOOP_BREAK_INTERVAL
from timon.probes.probe_if import mk_probe

logger = logging.getLogger(__name__)


async def ask_exit(signame, stopevent, cfg):
    """
    This code is an attempt to help performing a
    clean shutdown.
    First time the signal is caught, set an asyncio event to
    True that permits to not relaunch the loop and cleanly stop after
    probes process.
    Second time the signal is caught, abruptly stop timon (
    but cleanly stop plugins and the dbstore to avoid loosing data)
    """
    logger.info("got signal %r: will ask exit", signame)
    if not stopevent.is_set():
        stopevent.set()
    else:
        logger.warning("Second stop signal: Force exit")
        try:
            async with asyncio.timeout(5):
                await cfg.stop_plugins()
                cfg.stop_dbstore()
        except Exception:
            logger.exception("Cannot properly stop dbstore or plugins")
        sys.exit()


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
    logger.debug(
        "Start shell loop with a delay of %r and with args = %r",
        delay, args)

    mydir = os.path.dirname(__file__)
    shell_cmd = os.path.join(mydir, 'data', 'scripts', 'timonloop.sh')

    pydir = os.path.realpath(os.path.dirname(sys.executable))
    os.environ['PATH'] = os.environ['PATH'] + os.pathsep + os.path.join(pydir)
    # call execl: This will never return
    os.execl(shell_cmd, shell_cmd, str(delay), *args)


async def run_once(options, first=False, cfg=None):
    """ runs one probe iteration
        returns:
            (t_next, notifiers)
            t_next: in how many seconds the next probe should be fired
            notifiers: list of notifiers, that were started
    """
    logger.info("Start run once with options=%r", options)
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
    runner = Runner(probes, queue)
    t_next = await runner.run(force=options.probe)

    cfg.save_state()

    t = time.time()
    t_delta_next = max(t_next - t, 0)

    if runner.notifier_objs:
        # rem: `notifier_objs` is the list of notifiers
        # that had `shall_notify` True
        for notifier in runner.notifier_objs:
            # note: `notifier.notify` is the bound method
            # in `timon.notifiers.base:Notifier`
            runner.notifiers.append(notifier.notify)
        return t_delta_next, runner.notifiers

    return max(t_next - t, 0), []


async def run_loop(options, cfg, run_once_func=run_once, t00=None):
    """
    the async application loop
    """
    paranoia_loop = options.paranoia_loop
    paranoia_time_break = False
    ts = time.time()
    if paranoia_loop:
        logger.info("RUNMODE PARANO")
        start_time = time.time()
        end_planned_time = start_time + PARANOIA_LOOP_BREAK_INTERVAL
    logger.debug(
        "Start run_loop with t00=%r, run_once_func=%r and options=%r",
        t00, run_once_func, options)
    first = True
    dly, notifiers = None, None
    loop = asyncio.get_running_loop()
    stopevent = asyncio.Event()
    # Signal handling
    for signame in ('SIGINT', 'SIGTERM'):
        loop.add_signal_handler(
            getattr(signal, signame),
            lambda: asyncio.create_task(ask_exit(signame, stopevent, cfg))
        )
    await cfg.start_plugins()
    while not stopevent.is_set():
        # TODO: clean all_notifiers
        # print("OPTIONS:\n", options)
        t0 = time.time()  # now
        logger.debug("RO @%7.3f", t0 - t00)
        dly, notifiers = await run_once(
                options, cfg=cfg, first=first)
        logger.debug("end of run_once")
        first = False
        t1 = time.time()  # now
        logger.debug("RODONE @%7.3f", t1 - t00)
        if not options.loop:
            break
        if paranoia_loop and t1 >= end_planned_time:
            paranoia_time_break = True
            break
        if notifiers:
            async with asyncio.TaskGroup() as async_tg:
                # note: is a list of `Notifier.notify` (see `run_once`)
                for notifier in notifiers:
                    async_tg.create_task(notifier())
        dly = dly - (t1 - t0)
        logger.debug("DLY = %7.3f", dly)
        if dly > 0:
            logger.info("sleep %f", dly)
            try:
                await asyncio.wait_for(stopevent.wait(), timeout=dly)
            except TimeoutError:
                pass
    if notifiers:
        async with asyncio.TaskGroup() as async_tg:
            # note: is a list of `Notifier.notify` (see `run_once`)
            for notifier in notifiers:
                logger.debug("wait for notifier %s", str(notifier))
                async_tg.create_task(notifier())
                logger.debug("notifier done")
    await cfg.stop_plugins()
    cfg.stop_dbstore()
    if paranoia_loop and paranoia_time_break and not stopevent.is_set():
        logger.info("PARANO END LOOP will start another subproc")
        os.execl(sys.argv[0], *sys.argv)
    tx = time.time()
    logger.critical("took %d sec", tx-ts)
    return dly, notifiers


def run(options):
    """
    starting point for a run
    """
    t00 = time.time()  # now
    # print("OPTIONS:\n", options)
    if options.shell_loop:
        exec_shell_loop(sys.argv[1:], options.loop_delay)
        return  # just to make it more obvious. previous line never returns

    cfg = timon.conf.config.get_config(options=options)
    if options.paranoia_loop:
        options.loop = True
    return asyncio.run(
        run_loop(options=options, cfg=cfg, run_once_func=run_once, t00=t00))
