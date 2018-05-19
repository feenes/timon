import asyncio
import random
import time
import logging

from .probes import HttpProbe, ThreadProbe, ShellProbe

from .config import get_config

logger = logging.getLogger()


class Runner:
    """
    class that runs all passed probes and gathers the results
    and starts notifiers if a statechange passes the filter rules
    """
    def __init__(self, probes=None, queue=None,
                 cfg=None, run_till_idle=True, loop=None):
        """
        creates and parametrizes a runner
        :param probes: list of probes to run
        :param queue: queue with probetimes and probes to run
        :param cfg: global timon config
        :param run_till_idle: bool. if True runs till each probe has been
                executed at least once
        :loop the asyncio loop to be used
        """
        self.probes = probes if probes is not None else []
        self.queue = queue
        self.notifiers = []
        self.run_till_idle = run_till_idle
        self.loop = loop if loop else asyncio.get_event_loop()
        self.cfg = cfg or get_config()

    async def run(self, t0=None, force=True):
        """
        starts runner depending on its conf
        """
        t0 = t0 if t0 is not None else time.time()
        if self.run_till_idle:
            await self._run_till_idle(self.probes, t0)  # use retval?
            if not force:
                # TODO: not sure what the logic here is. Please recheck
                # time when next evt shall be executed.
                self.queue.t_next()  # use retval?
        if not force:
            return self.queue.t_next()  # time when next evt shall be executed.
        return t0

    async def _run_till_idle(self, probes, t0):
        """
        runs each probe once and waits waits for them to be completed.
        :param probes: probes to be run
        :param t0:
        """
        probe_tasks = []
        probes = list(probes)  # for debugging
        print("%d probes to run" % len(probes))
        for probe in probes:
            probe.done_cb = self.probe_done
            probe_tasks.append(probe.run())
        await asyncio.gather(*probe_tasks)
        t = time.time()
        delta_t = t - t0
        print("Execution time %.1f" % delta_t)
        return t

    async def probe_done(self, probe, status=None, msg="?"):
        """
        call back to be executed when probe execution is finished
        """
        print("DONE: ", probe, status)
        queue = self.queue
        cfg = self.cfg
        now = time.time()
        state = cfg.get_state()

        changed = state.update_probe_state(
                probe, status=status, t=now, msg=msg)

        probe_state = state.get_probe_state(probe)

        if changed:
            # FLAP detection etc missing here
            # This is just a simple change detection
            print("Status changed to %s." % status)
            for notifier_name in probe.notifiers:
                print("check notifier", notifier_name)
                notifier = cfg.get_notifier(notifier_name)
                if notifier.shall_notify(probe, probe_state):
                    task = self.loop.create_task(
                        notifier.notify(probe, probe_state))
                    self.notifiers.append(task)

        if queue:
            # reschedule depending on status
            if status in ["OK", "UNKNOWN"]:
                t_next = max(now, probe.t_next + probe.interval)
            else:
                t_next = max(now, probe.t_next + probe.failinterval)
            sched_entry = cfg.mk_sched_entry(
                name=probe.name,
                t_next=t_next,
                interval=probe.interval,
                failinterval=probe.failinterval,
            )
            self.queue.add(sched_entry)
            logger.debug("Q %s", repr(self.queue))

    def close(self):
        self.loop.close()


def main():
    """ very basic main function to show case running of probes """
    print("runner")
    urls = [
        "https://www.github.com",
        "https://www.google.com",
        "https://www.teledomic.eu",
    ]
    runner = Runner()
    # stop_on_idle = True
    for url in urls:
        probe_cls = random.choice((HttpProbe, ThreadProbe, ShellProbe))
        runner.probes.append(probe_cls(url))

    loop = asyncio.get_event_loop()
    loop.run_until_complete(runner.run())
    runner.run()


if __name__ == "__main__":
    main()
