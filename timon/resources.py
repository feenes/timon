import os
from asyncio import Semaphore

resource_info = dict([
    # max parallel subprocesses
    ("subproc", int(os.environ.get("TIMON_RSRC_SUBPROC", "3"))),
    # max parallel network accesses
    ("network", int(os.environ.get("TIMON_RSRC_NETWORK", "30"))),
    # max parallel threads
    ("threads", int(os.environ.get("TIMON_RSRC_THREADS", "10"))),
    ])


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

    @classmethod
    def get(cls, name):
        return cls.rsrc_tab[name]


TiMonResource.add_resources(resource_info)


def get_resource(cls):
    """ gets the resource of a timon class if existing """
    if not cls.resources:
        return None
    resources = cls.resources
    assert len(resources) == 1
    return TiMonResource.get(resources[0])


async def acquire_rsrc(cls):
    """ acquires resource of a timon class if existing """
    rsrc = get_resource(cls)
    if rsrc:
        print("GET RSRC", cls.resources)
        await rsrc.acquire()
        print("GOT RSRC", cls.resources)
