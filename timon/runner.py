import asyncio
import time
import random
from asyncio import coroutine
from asyncio import sleep

from .probes import HttpProbe, ThreadProbe, ShellProbe

urls = [
    "http://noma.dungeon.de",
    "https://noma2.dungeon.de",
    "https://noma.teledomic.eu",
    "https://office.mhcomm.fr",
]


class Runner:
    """ class that runs all the probes and gathers the results """

    def __init__(self, probes=None, run_till_idle=True):
        """ creates and parametrizes a runner """
        self.run_till_idle = run_till_idle
        self.probes = probes if probes is not None else []
        self.loop = asyncio.get_event_loop()

    def run(self, t0=None):
        """ starts runner depending on its conf """
        t0 = t0 if t0 is not None else time.time()
        if self.run_till_idle:
            return self._run_till_idle(self.probes, t0)

    def _run_till_idle(self, probes, t0):
        """ runs until scheduler idle (no more tasks to execute """
        probe_tasks = [ probe.run() for probe in probes ]
        self.loop.run_until_complete(asyncio.gather(*probe_tasks))
        t = time.time()
        delta_t = t - t0
        print("Execution time %.1f" % delta_t)
        return t
    

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
