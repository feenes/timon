"""
#############################################################################
Copyright : (C) 2017 by Teledomic.eu All rights reserved

Name:         timon.probes

Description:  timon base classes for probes and most important probes

#############################################################################

"""

import json
import logging
import os
import random
import re
import sys
import time

from asyncio import coroutine
from asyncio import create_subprocess_exec
from asyncio import Semaphore
from asyncio import sleep
from asyncio import subprocess

import minibelt

from timon.config import get_config

import timon.scripts.flags as flags

#  just for demo. pls move later to conf
resource_info = dict([
    # max parallel subprocesses
    ("subproc", int(os.environ.get("TIMON_RSRC_SUBPROC", "3"))),
    # max parallel network accesses
    ("network", int(os.environ.get("TIMON_RSRC_NETWORK", "30"))),
    # max parallel threads
    ("threads", int(os.environ.get("TIMON_RSRC_THREADS", "10"))),
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
    """
    baseclass for timon probes
    """
    resources = tuple()

    def __init__(self, **kwargs):
        cls = self.__class__
        assert len(cls.resources) <= 1
        unhandled_args = {}
        self.name = kwargs.pop('name')
        self.t_next = kwargs.pop('t_next')
        self.interval = kwargs.pop('interval')
        self.failinterval = kwargs.pop('failinterval')
        self.notifiers = kwargs.pop('notifiers', [])

        # try to determine unhandled_args
        unhandled_args.update(kwargs)
        for ok_arg in ['schedule', 'done_cb', 'probe', 'cls', 'host']:
            unhandled_args.pop(ok_arg, None)

        self.status = "UNKNOWN"
        self.msg = "-"
        self.done_cb = None

        # Still not really working, but intended to handle detection
        # of bad kwargs (obsolete / typos)
        if unhandled_args:
            logger.warning("unhandled init args %r", unhandled_args)

    @coroutine
    def run(self):
        """ runs one task """
        cls = self.__class__
        name = self.name
        rsrc = TiMonResource.get(cls.resources[0]) if cls.resources else None
        if rsrc:
            # print("GET RSRC", cls.resources)
            yield from rsrc.acquire()
            print("GOT RSRC", cls.resources)

        try:
            logger.debug("started probe %r", name)
            yield from self.probe_action()
            logger.debug("finished probe %r", name)
            if rsrc:
                # print("RLS RSRC", cls.resources)
                rsrc.release()
                print("RLSD RSRC", cls.resources)
            rsrc = None
        except Exception:
            if rsrc:
                rsrc.release()
            raise
        if self.done_cb:
            yield from self.done_cb(self, status=self.status, msg=self.msg)

    @coroutine
    def probe_action(self):
        """ this is the real probe action and should be overloaded """

    def __repr__(self):
        return repr("%s(%s)@%s" % (self.__class__, self.name, time.time()))


class SubProcBprobe(Probe):
    """
    A probe using a subprocess
    """
    resources = ("subproc",)

    def __init__(self, **kwargs):
        """
        :param cmd: command to execute

        also inherits params from Probe
        """
        self.cmd = kwargs.pop('cmd')
        super().__init__(**kwargs)

    def create_final_command(self):
        """
        helper to create the command that should
        finally be called.
        """
        cmd = self.cmd
        if not cmd:
            logger.critical("command is missing")
            return

        final_cmd = []
        for entry in cmd:
            if callable(entry):
                entry = entry()
            final_cmd.append(entry)
        logger.info("shall call %s", ' '.join(cmd))
        print(" ".join(final_cmd))
        return final_cmd

    @coroutine
    def probe_action(self):
        final_cmd = self.create_final_command()
        print(" ".join(final_cmd))
        process = yield from create_subprocess_exec(
            *final_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
            )

        stdout, _ = yield from process.communicate()
        self.status, self.msg = stdout.decode().split(None, 1)
        # print("STDOUT", stdout)
        # logger.debug("PROC %s finished", final_cmd)
        logger.debug("PROC RETURNED: %s", stdout)


class SubProcModProbe(SubProcBprobe):
    """
    A subprocess probe calling the passed module
    """
    def __init__(self, **kwargs):
        """
        also inherits params from SubProcBprobe except 'cmd', which
        will be overridden
        """
        cls = self.__class__
        assert 'cmd' not in kwargs
        kwargs['cmd'] = [sys.executable, "-m", cls.script_module]
        super().__init__(**kwargs)


class HttpProbe(SubProcBprobe):
    """
    probe performing an HTTP request.
    Initial version implemented as subprocess.
    Should be implemented lateron as thread or
    as aiohttp code
    """
    script_module = ""  # module to execute as command

    def __init__(self, **kwargs):
        """
        :param host: host name (as in config)
        :param verify_ssl: whether ssl server cert should be verified
        - 2 ways to pass url (CAUTION: Use only 1 of 2):
        - PASS COMPLETE URL
            :param url: complete_url on which request should be performed to
            :param url_params: params to pass to url via % formatters
                            (Caution: order is important)
                    EXAMPLE:
                    Next params :
                    url: 'http://titi/%s/%s/croq/'
                    url_params:
                        - 'Hello'
                        - 'World'

                    Yields final url:
                    'http://titi/Hello/World/croq/'

        -PASS URL PARAMS
            :param url_param: which probe param contains the relative url
            :param urlpath: default url path if urlparam not set

        also inherits params from SubProcBprobe except 'cmd', which
        will be overridden
        """
        cls = self.__class__
        host_id = kwargs.pop('host', None)
        hostcfg = get_config().cfg['hosts'][host_id]
        verify_ssl = kwargs.pop('verify_ssl', None)
        send_cert = kwargs.pop('send_cert', False)
        client_cert = hostcfg.get('client_cert', None)
        base_url = kwargs.pop("url", None)
        if base_url:
            url_params_name = kwargs.pop('url_params', None)
            url_params = []
            if url_params_name:
                for param in url_params_name:
                    url_params.append(
                        minibelt.get(hostcfg, keys=param.split(".")) or param)
            complete_url = base_url % tuple(url_params)
            self.url = url = complete_url
        else:
            url_param = kwargs.pop('url_param', 'urlpath')
            if url_param != 'urlpath':
                kwargs.pop('urlpath', None)
            url_param_val = kwargs.pop(url_param, None)
            rel_url = hostcfg.get(url_param) or url_param_val or ""
            hostname = hostcfg['hostname']
            proto = hostcfg['proto']
            port = hostcfg['port']
            self.url = url = "%s://%s:%d/%s" % (proto, hostname, port, rel_url)
        assert 'cmd' not in kwargs
        cmd = kwargs['cmd'] = [sys.executable, "-m", cls.script_module]
        super().__init__(**kwargs)

        # TODO: debug / understand param passing a little better
        # perhaps there's a more generic way of 'mixing' hostcfg / kwargs
        # print("HOSTCFG", hostcfg)

        # print(url)
        cmd.append(url)
        if verify_ssl is not None:
            cmd.append('--verify_ssl=' + str(verify_ssl))
        if send_cert:
            cmd.append('--cert=' + client_cert[0])
            cmd.append('--key=' + client_cert[1])

    def __repr__(self):
        return repr("%s(%s)" % (self.__class__, self.name))


class ThreadProbe(Probe):
    @coroutine
    def probe_action(self):
        print("THREAD")
        yield from sleep(random.random()*1)


ShellProbe = ThreadProbe


class HttpIsUpProbe(HttpProbe):
    script_module = "timon.scripts.isup"


class SSLCertProbe(SubProcModProbe):
    """ Verify whether an SSL cert is expired
        or will expire soon
    """
    script_module = "timon.scripts.cert_check"

    def __init__(self, **kwargs):
        # cls = self.__class__
        host_id = kwargs.pop('host', None)
        hostcfg = get_config().cfg['hosts'][host_id]
        super().__init__(**kwargs)
        host_str = "%s:%s" % (
            hostcfg.get("hostname"),
            hostcfg.get("port", "443")
            )
        self.cmd.append(host_str)
        # print(vars(self))


class SSLClientCAProbe(SubProcModProbe):
    """ Verify whether an SSL Server says, that it accepts certs signed
        by a given CA
    """
    script_module = "timon.scripts.clientca_check"

    def __init__(self, **kwargs):
        """
        :param host: timon host that shall be probed
        :param ca_rex: regular expression that shall match the CA string
                  with format C=../ST=../L=../O=../OU=..CN=../emailAddress=..

        host config vars:
            hostname: name of ssl host
            port: port to connect to SSL host
        """
        host_id = kwargs.pop('host', None)
        hostcfg = get_config().cfg['hosts'][host_id]
        ca_rex = kwargs.pop('ca_rex', ".")
        super().__init__(**kwargs)
        host_str = "%s:%s" % (
            hostcfg.get("hostname"),
            hostcfg.get("port", "443")
            )
        self.cmd.append(host_str)
        self.cmd.append(ca_rex)
        # print(vars(self))


class HttpJsonProbe(HttpProbe):
    script_module = "timon.scripts.http_json"

    def __init__(self, **kwargs):
        self.ok_rule = kwargs.pop('ok_rule', None)
        self.warning_rule = kwargs.pop('warning_rule', None)
        self.error_rule = kwargs.pop('error_rule', None)
        super().__init__(**kwargs)

    def match_rule(self, rslt, rule):
        name, regex = rule.split(':', 1)
        val = rslt
        for field in name.split('.'):
            val = val.get(field, {})
        val = str(val)
        return bool(re.match(regex, val))

    @coroutine
    def probe_action(self):
        final_cmd = self.create_final_command()
        process = yield from create_subprocess_exec(
            *final_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
            )

        stdout, _ = yield from process.communicate()
        print("STDOUT", stdout)
        jsonstr = stdout.decode()
        logger.debug("jsonstr %s", jsonstr)
        self.status = "UNKNOWN"
        self.msg = "bla"
        rslt = json.loads(jsonstr)
        logger.debug("rslt %r", rslt)
        resp = rslt['response']
        logger.debug("resp %r", resp)

        exit_code = rslt['exit_code']
        if exit_code == flags.FLAG_UNKNOWN:
            return
        self.msg = resp.get('msg') or rslt.get('reason') or ''
        if self.match_rule(rslt, self.ok_rule):
            self.status = "OK"
        elif self.match_rule(rslt, self.warning_rule):
            self.status = "WARNING"
        elif self.match_rule(rslt, self.error_rule):
            self.status = "ERROR"


class DiskFreeProbe(Probe):
    pass


class HttpJsonIntervalProbe(HttpProbe):
    """
    probe checking if a value is:
        - between 2 values (example: "key1.key2:[0, 20]")
        - greater than a value (example: "key1.key2.key3>60")
        - lesser than a value (example: "key<20")
        - equal to a value (example: "key1.key2:200")
    """
    script_module = "timon.scripts.http_json"

    def __init__(self, **kwargs):
        self.ok_rule = kwargs.pop('ok_rule', None)
        self.warning_rule = kwargs.pop('warning_rule', None)
        super().__init__(**kwargs)

    def match_rule(self, rslt, rule):
        rule_types = {
            "equal_rule": re.compile(r"^(.*):([a-zA-Z0-9]+)$"),
            "greater_rule": re.compile(r"^(.*)>(\d+)$"),
            "lesser_rule": re.compile(r"^(.*)<(\d+)$"),
            "interval_rule": re.compile(r"^(.*):\[(\d+),\s*(\d+)\]$"),
            }

        def check_match_rule(rule):
            for rule_type, rule_rex in rule_types.items():
                match = rule_rex.match(rule)
                if match:
                    return rule_type, match
            return None, None

        rule_type, match = check_match_rule(rule)
        if rule_type:
            fields = match.groups()[0].split(".")
            rule_val = match.groups()[1:]
            val = minibelt.get(rslt, keys=fields)
            if rule_type == "equal_rule":
                return str(val) == rule_val[0]
            elif rule_type == "greater_rule":
                return float(val) > float(rule_val[0])
            elif rule_type == "lesser_rule":
                return float(val) < float(rule_val[0])
            elif rule_type == "interval_rule":
                return (float(rule_val[0]) < float(val)
                        < float(rule_val[1]))
        return

    @coroutine
    def probe_action(self):
        final_cmd = self.create_final_command()
        process = yield from create_subprocess_exec(
            *final_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
            )

        stdout, _ = yield from process.communicate()
        print("STDOUT", stdout)
        jsonstr = stdout.decode()
        logger.debug("jsonstr %s", jsonstr)
        rslt = json.loads(jsonstr)
        logger.debug("rslt %r", rslt)
        resp = rslt['response']
        logger.debug("resp %r", resp)

        exit_code = rslt['exit_code']
        if exit_code == flags.FLAG_UNKNOWN:
            return
        self.msg = resp.get('msg') or rslt.get('reason') or ''
        if rslt.get("status") != 200:
            self.status = " UNKNOWN"
        elif self.match_rule(rslt, self.ok_rule):
            self.status = "OK"
        elif self.warning_rule and self.match_rule(rslt, self.warning_rule):
            self.status = "WARNING"
        else:
            self.status = "ERROR"
        print(self.status)
