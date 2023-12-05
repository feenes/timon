import logging
import os

from trio import Semaphore

logger = logging.getLogger(__name__)

resource_info = dict([
    # max parallel subprocesses
    ("subproc", int(os.environ.get("TIMON_RSRC_SUBPROC", "3"))),
    # max parallel network accesses
    ("network", int(os.environ.get("TIMON_RSRC_NETWORK", "30"))),
    # max parallel threads
    ("threads", int(os.environ.get("TIMON_RSRC_THREADS", "10"))),
    ])


class TiMonResource():
    """ intended to manage limited resources with a counter """
    rsrc_tab = {}

    def __init__(self, name, count):
        self.name = name
        self.count = count
        self.semaph = Semaphore(count)

    @classmethod
    def add_resources(cls, entries):
        for name, count in resource_info.items():
            rsrc = cls(name, count)
            cls.rsrc_tab[name] = rsrc

    @classmethod
    def get(cls, name):
        return cls.rsrc_tab[name]

    @classmethod
    def get_all(cls):
        """
        Returns all resources
        """
        return cls.rsrc_tab


TiMonResource.add_resources(resource_info)


def get_resource(cls):
    """ gets the resource of a timon class if existing """
    if not cls.resources:
        return None
    resources = cls.resources
    assert len(resources) == 1
    return TiMonResource.get(resources[0])


def get_all_resources():
    """
    Returns all resources
    """
    return TiMonResource.get_all()


async def acquire_rsrc(cls):
    """ acquires resource of a timon class if existing """
    rsrc = get_resource(cls)
    if rsrc:
        logger.debug("GET RSRC %r", cls.resources)
        await rsrc.semaph.acquire()
        logger.debug("GOT RSRC %r", cls.resources)
        return rsrc
