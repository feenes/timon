"""
#############################################################################
Copyright : (C) 2017 by Teledomic.eu All rights reserved

Name:         timon.probes

Description:  timon base classes for probes and most important probes

#############################################################################
 
"""
import sys
import logging
import asyncio
import time
from asyncio import coroutine
from asyncio import Semaphore
from asyncio import subprocess
from asyncio import create_subprocess_exec

from timon.config import get_config

#  just for demo. pls remove later
import random
from asyncio import sleep
resource_info = dict([
#    ("network", 30), # handle directly with asyncio objects
#    ("threads", 10), # handle with asyncio objects
    ("subproc", 3), # handle with asyncio objects
])

logger = logging.getLogger(__name__)


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
        
class Probe:
    """ baseclass for timon probes """
    resources = tuple()
    def __init__(self, **kwargs):
        cls = self.__class__
        assert len(cls.resources ) <= 1
        self.name = kwargs.pop('name')
        self.t_next = kwargs.pop('t_next')
        self.interval = kwargs.pop('interval')
        self.failinterval = kwargs.pop('failinterval')
        self.status = "UNKNOWN"
        self.done_cb = None

    @coroutine
    def run(self):
        """ runs one task """
        cls = self.__class__
        name = self.name
        rsrc = TiMonResource.get(cls.resources[0]) if cls.resources else None
        if rsrc:
            print("GET RSRC", cls.resources)
            yield from rsrc.acquire()
            print("GOT RSRC", cls.resources)
        try:
            logger.debug("started probe %r", name)
            yield from self.probe_action()
            logger.debug("finished probe %r", name)
            if rsrc:
                print("RLS RSRC", cls.resources)
                rsrc.release()
                print("RLSD RSRC", cls.resources)
            rsrc = None
        except Exception:
            if rsrc:
                rsrc.release()
            raise
        if self.done_cb:
            yield from self.done_cb(self, status=self.status)

    @coroutine
    def probe_action(self):
        """ this is the real probe action and should be overloaded """

    def __repr__(self):
        return repr("%s(%s)@%s" % (self.__class__, self.name, time.time()))


class SubProcBprobe(Probe):
    resources = ("subproc",)
    def __init__(self, **kwargs):
        """
            :param cmd: command to execute
            also inherits params from Probe
        """
        self.cmd = kwargs.get('cmd')
        super().__init__(**kwargs)

    @coroutine
    def probe_action(self):
        logger.debug("SHELL")
        cmd = self.cmd
        if not cmd:
            print("no command. will sleep instead")
            yield from sleep(random.random()*1)
            return

        final_cmd = []
        for entry in cmd:
            if  callable(entry):
                entry = entry()
            final_cmd.append(entry)
        logger.info("shall call %r", cmd)
        print(" ".join(final_cmd))
        process = yield from create_subprocess_exec(
            *final_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
            )

        stdout, _ = yield from process.communicate()
        self.status = stdout.split(None, 1)[0].decode()
        #print("STDOUT", stdout)
        logger.debug("PROC RETURNED: %s", stdout)


class HttpProbe(SubProcBprobe):
    def __init__(self, **kwargs):
        """
            :param host: host name (as in config)
            also inherits params from SubProcBprobe
        """
        #print("KWARGS", kwargs)
        host_id = kwargs.get('host')
        hostcfg = get_config().cfg['hosts'][host_id]
        verify_ssl = kwargs.get('verify_ssl', None)
        # TODO: debug / understand param passing a little better
        # perhaps there's a more generic way of 'mixing' hastcfg / kwargs
        send_cert = hostcfg.get('send_cert')
        client_cert = hostcfg.get('client_cert')
        #print("HOSTCFG", hostcfg)
        
        hostname = hostcfg['hostname']
        proto = hostcfg['proto']
        port = hostcfg['port']
        rel_url = hostcfg['urlpath']
        #print("MKURL", (proto, hostname, port, rel_url))
        self.url = url = "%s://%s:%d/%s" % (proto, hostname, port, rel_url)
        #print(url)
        cmd = kwargs['cmd'] = [ sys.executable, "-m", "timon.scripts.isup",  url ]
        if verify_ssl is not None:
            cmd.append('--verify_ssl=' + str(verify_ssl))
        if send_cert:
            cmd.append('--cert=' + client_cert[0])
            cmd.append('--key=' + client_cert[1])

        super().__init__(**kwargs)
        #print("ISUP KWARGS: ", kwargs)

    def __repr__(self):
        return repr("%s(%s)" % (self.__class__, self.name))




class ThreadProbe(Probe):
    @coroutine
    def probe_action(self):
        print("THREAD")
        yield from sleep(random.random()*1)

ShellProbe = ThreadProbe

class HttpIsUpProbe(HttpProbe):
    pass

class DiskFreeProbe(Probe):
    pass

