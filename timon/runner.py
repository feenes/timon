import asyncio
import time
import random
from asyncio import coroutine
from asyncio import sleep

from .probes import HttpProbe, ThreadProbe, ShellProbe

from .config import get_config

urls = [
    "http://noma.dungeon.de",
    "https://noma2.dungeon.de",
    "https://noma.teledomic.eu",
    "https://office.mhcomm.fr",
]


class Runner:
    """ class that runs all passed probes and gathers the results """

    def __init__(self, probes=None, queue=None, cfg=None, run_till_idle=True, loop=None):
        """ creates and parametrizes a runner """
        self.probes = probes if probes is not None else []
        self.queue = queue
        self.run_till_idle = run_till_idle
        self.loop = loop if loop else asyncio.get_event_loop()
        self.cfg = cfg or get_config()

    def run(self, t0=None, force=True):
        """ starts runner depending on its conf """

        t0 = t0 if t0 is not None else time.time()
        if self.run_till_idle:
            rslt = self._run_till_idle(self.probes, t0)
            if not force:
                t_nxt = self.queue.t_next() # time when next even is there to be executed.
        if not force:
            return self.queue.t_next() # time when next even is there to be executed.
        return t0
    
    def _run_till_idle(self, probes, t0):
        """ 
        runs until scheduler idle (no more tasks to execute 
        :param t0:
        """
        probe_tasks = []
        probes = list(probes) # for debugging
        print("%d probes to run" % len(probes))
        for probe in probes:
            probe.done_cb = self.probe_done
            probe_tasks.append(probe.run())
        self.loop.run_until_complete(asyncio.gather(*probe_tasks))
        t = time.time()
        delta_t = t - t0
        print("Execution time %.1f" % delta_t)
        return t

    @coroutine
    def probe_done(self, probe, status=None):
        print("DONE: ", probe, status)
        queue = self.queue
        if queue:
            cfg = self.cfg
            now = time.time()
            state = cfg.get_state()

            state.update_probe_state(probe.name, status=status,
                    t=now, msg="?")

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

    def close(self):
        self.loop.close()
                
    
    

def main():
    """ very basic main function to show case running of probes """
    print("runner")
    runner = Runner()
    stop_on_idle = True
    probes = []
    for url in urls:
        probe_cls = random.choice((HttpProbe, ThreadProbe, ShellProbe))
        runner.probes.append(probe_cls(url))

    runner.run()

if __name__ == "__main__":
    main()
