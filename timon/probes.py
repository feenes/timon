import asyncio
import time
from asyncio import coroutine
from asyncio import Semaphore

#  just for demo. pls remove later
import random
from asyncio import sleep
resource_info = dict( 
#    ("network", 30), # handle directly with asyncio objects
#    ("threads", 10), # handle with asyncio objects
#    ("subproc", 30), # handle with asyncio objects
)


class TiMonResource(Semaphore):
    """ intended to manage limited resources with a counter """
    rsrc_tab = {}
    def __init__(self, name, count):
        self.name = name
        self.count = count
        Semaphore.__init__(self, count)

    @classmethod 
    def add_resources(cls, entries):
        for name, count in resource_info.items():
            rsrc = cls(name, count)
            cls.rsrc_tab[name] = rsrc

        
class Probe:
    """ baseclass for timon probes """
    resources = tuple()
    def __init__(self, name, *args, **_kwargs):
        name = name
        cls = self.__class__
        self.name = name

    @coroutine
    def run(self):
        """ runs one task """
        cls = self.__class__
        name = self.name
        print("started probe", name)
        yield from self.probe_action()
        print("finished probe", name)

    @coroutine
    def probe_action(self):
        """ this is the real probe action and should be overloaded """


class HttpProbe(Probe):
    @coroutine
    def probe_action(self):
        print("HTTP")
        yield from sleep(random.random()*2)


class ThreadProbe(Probe):
    @coroutine
    def probe_action(self):
        print("THREAD")
        yield from sleep(random.random()*1)


class ShellProbe(Probe):
    @coroutine
    def probe_action(self):
        print("SHELL")
        yield from sleep(random.random()*1)

class IsUpProbe(ShellProbe):
    pass

class DiskFreeProbe(ShellProbe):
    pass

