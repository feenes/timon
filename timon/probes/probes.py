"""
#############################################################################
Copyright : (C) 2017 by Teledomic.eu All rights reserved

Name:         timon.probes.probes

Description:  timon base classes for probes and most important probes

#############################################################################

"""
import asyncio
import logging
import random
import re
import ssl
import sys
import time

import httpx
import minibelt

from timon import resources
from timon.conf.config import get_config

logger = logging.getLogger(__name__)


class Probe:
    """
    baseclass for timon probes
    """
    resources = tuple()

    def __init__(self, **kwargs):
        self._init_part1(kwargs)
        self._init_check_args(kwargs)

    def _init_part1(self, kwargs):
        """
        starting part for a timon  probe
        """
        cls = self.__class__
        assert len(cls.resources) <= 1
        self.name = kwargs.pop('name')
        self.t_next = kwargs.pop('t_next')
        self.interval = kwargs.pop('interval')
        self.failinterval = kwargs.pop('failinterval')
        self.notifiers = kwargs.pop('notifiers', [])

        self.status = "UNKNOWN"
        self.msg = "-"
        self.done_cb = None

    def _init_check_args(self, kwargs):
        # Still not really working, but intended to handle detection
        # of bad kwargs (obsolete / typos)
        unhandled_args = {}
        kwargs.pop("extra", {})

        # try to determine unhandled_args
        unhandled_args.update(kwargs)
        for ok_arg in ['schedule', 'done_cb', 'probe', 'cls', 'host']:
            unhandled_args.pop(ok_arg, None)

        if unhandled_args:
            logger.warning("unhandled init args %r", unhandled_args)

    def get_resource(self):
        cls = self.__class__
        return resources.get_resource(cls)

    async def run(self):
        """ runs one task """
        cls = self.__class__
        name = self.name
        rsrc = await resources.acquire_rsrc(cls)
        try:
            logger.debug("started probe %r", name)
            await self.probe_action()
            logger.debug("finished probe %r", name)
        except Exception:
            raise
        finally:
            if rsrc:
                rsrc.semaph.release()
                logger.debug("RLSD RSRC %r", rsrc)
        if self.done_cb:
            await self.done_cb(self, status=self.status, msg=self.msg)

    async def probe_action(self):
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
        self.timeout = kwargs.pop('timeout', 90)
        self.timeout_task = None
        self.timed_out = False
        self.process = None
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
        logger.debug(" ".join(final_cmd))
        return final_cmd

    async def probe_action(self):
        final_cmd = self.create_final_command()
        logger.debug(" ".join(final_cmd))
        self.process = await asyncio.create_subprocess_exec(
            *final_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,)
        stdout, _ = await self.process.communicate()
        if not self.timed_out:
            self.status, self.msg = stdout.decode().split(None, 1)
        else:
            self.status = "ERROR"
            self.msg = "Subproc Timed out"
            logger.warning("PROC %s timed out", final_cmd)
        logger.debug("PROC RETURNED: %s", stdout)

    # def timeout_call(self):
    # TODO: implement a subprocess timeout
    #     self.timed_out = True
    #     self.process.kill()


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


class HttpProbe(Probe):
    """
    probe performing an HTTP request.
    """
    resources = ("network",)

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
        host_id = kwargs.pop('host', None)
        hostcfg = get_config().cfg['hosts'][host_id]
        self.verify_ssl = kwargs.pop('verify_ssl', None)
        send_cert = kwargs.pop('send_cert', False)
        client_cert = hostcfg.get('client_cert', None)
        if send_cert and client_cert:
            sslcontext = ssl.create_default_context()
            sslcontext.load_cert_chain(client_cert[0], client_cert[1])
            self.verify_ssl = sslcontext
        base_url = kwargs.pop("url", None)
        if base_url:
            url_params_name = kwargs.pop('url_params', None)
            url_params = []
            if url_params_name:
                for param in url_params_name:
                    url_params.append(
                        minibelt.get(hostcfg, *param.split(".")) or param)

            complete_url = base_url % tuple(url_params)
            self.url = complete_url
        else:
            url_param = kwargs.pop('url_param', 'urlpath')
            if url_param != 'urlpath':
                kwargs.pop('urlpath', None)
            url_param_val = kwargs.pop(url_param, None)
            rel_url = hostcfg.get(url_param) or url_param_val or ""
            hostname = hostcfg['hostname']
            proto = hostcfg['proto']
            port = hostcfg['port']
            self.url = "%s://%s:%d/%s" % (proto, hostname, port, rel_url)
        super().__init__(**kwargs)

        # TODO: debug / understand param passing a little better
        # perhaps there's a more generic way of 'mixing' hostcfg / kwargs

    async def probe_action(self):
        result = dict(
            status=0,
            response={},
            reason=None,
            )

        try:
            async with httpx.AsyncClient(verify=self.verify_ssl,
                                         follow_redirects=True) as client:
                resp = await client.get(
                    self.url, timeout=10)
        except Exception as exc:
            result['reason'] = repr(exc)
            return result
        s_code = resp.status_code
        result['status'] = s_code
        if s_code == 404:
            result["reason"] = "http404: cannot retrieve probe file"
        elif s_code != 200:
            result["reason"] = f"http error {s_code}"
        else:
            result['response'] = resp
        return result

    def __repr__(self):
        return repr("%s(%s)" % (self.__class__, self.name))


class ThreadProbe(Probe):
    async def probe_action(self):
        await asyncio.sleep(random.random()*1)


ShellProbe = ThreadProbe


class HttpIsUpProbe(HttpProbe):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def probe_action(self):
        resp = await super().probe_action()
        s_code = resp["status"]
        self.status = "OK" if s_code in [200] else "ERROR"
        self.msg = str(s_code)
        if resp["reason"]:
            self.status = "ERROR"
            self.msg = resp["reason"]


class SSLCertProbe(SubProcModProbe):
    """ Verify whether an SSL cert is expired
        or will expire soon
    """
    script_module = "timon.scripts.cert_check"

    def __init__(self, **kwargs):
        host_id = kwargs.pop('host', None)
        hostcfg = get_config().cfg['hosts'][host_id]
        super().__init__(**kwargs)
        host_str = "%s:%s" % (
            hostcfg.get("hostname"),
            hostcfg.get("port", "443")
            )
        self.cmd.append(host_str)


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


class HttpJsonProbe(HttpProbe):

    def __init__(self, **kwargs):
        self.ok_rule = kwargs.pop('ok_rule', None)
        self.warning_rule = kwargs.pop('warning_rule', None)
        self.error_rule = kwargs.pop('error_rule', None)
        super().__init__(**kwargs)

    def match_rule(self, rslt, rule):
        if rule is None:
            return False
        if rule == "DEFAULT":
            return True
        name, regex = rule.split(':', 1)
        val = rslt
        for field in name.split('.'):
            val = val.get(field, {})
        val = str(val)
        return bool(re.match(regex, val))

    def parse_result(self, jsonresp):
        logger.debug("jsonstr %r", jsonresp)
        self.status = "UNKNOWN"
        self.msg = "bla"
        rslt = jsonresp
        logger.debug("rslt %r", rslt)
        resp = rslt['response']
        logger.debug("resp %r", resp)

        self.msg = resp.get('msg') or rslt.get('reason') or ''
        if self.match_rule(rslt, self.ok_rule):
            self.status = "OK"
        elif self.match_rule(rslt, self.warning_rule):
            self.msg += (
                f"probe rslt ({rslt}) doesn't pass warning rule "
                f"({self.warning_rule})"
            )
            self.status = "WARNING"
        elif self.match_rule(rslt, self.error_rule):
            self.msg += (
                f"probe rslt ({rslt}) doesn't pass error rule "
                f"({self.error_rule})"
            )
            self.status = "ERROR"

    def parse_json(self, resp):
        try:
            resp['response'] = resp['response'].json()
        except KeyError as keyexc:
            resp['reason'] = repr(keyexc)
            resp['response'] = {}
            logger.exception("No response in resp dict")
        except Exception as exc:
            resp['reason'] = repr(exc)
            resp['response'] = {}
            logger.exception("cannot json parse response")
        return resp

    async def probe_action(self):
        resp = await super().probe_action()
        if resp["reason"]:
            # Return if not 200
            self.status = "UNKNOWN"
            try:
                msg = f"{resp['reason']} (resp={vars(resp['response'])})"
            except Exception:
                msg = f"{resp.get('reason')} (resp={repr(resp.get('response'))})"  # noqa E501
            self.msg = msg
            return resp
        jsonresp = self.parse_json(resp)
        self.parse_result(jsonresp)
        return jsonresp


class DiskFreeProbe(Probe):
    pass


class HttpJsonIntervalProbe(HttpJsonProbe):
    """
    probe checking if a value is:
        - between 2 values (example: "key1.key2:[0, 20]")
        - greater than a value (example: "key1.key2.key3>60")
        - lesser than a value (example: "key<20")
        - equal to a value (example: "key1.key2:200")
    """

    def __init__(self, **kwargs):
        self.ok_rule = kwargs.pop('ok_rule', None)
        self.warning_rule = kwargs.pop('warning_rule', None)
        self.error_rule = kwargs.pop('error_rule', "DEFAULT")
        HttpProbe.__init__(self, **kwargs)

    def match_rule(self, rslt, rule):
        rule_types = {
            "equal_rule": re.compile(r"^(.*)[:=]([a-zA-Z0-9]+)$"),
            "greater_rule": re.compile(r"^(.*)>(\d+)$"),
            "lesser_rule": re.compile(r"^(.*)<(\d+)$"),
            "interval_rule": re.compile(r"^(.*)[:=]\[(\d+),\s*(\d+)\]$"),
            }

        def check_match_rule(rule):
            if rule is None:
                return "NONE", None  # rule is always false
            if rule == "DEFAULT":
                return "DEFAULT", None  # rule is DEFAULT
            for rule_type, rule_rex in rule_types.items():
                match = rule_rex.match(rule)
                if match:
                    return rule_type, match
            return None, None

        rule_type, match = check_match_rule(rule)
        if rule_type:
            if rule_type == "NONE":
                return False
            if rule_type == "DEFAULT":
                return True
            fields = match.groups()[0].split(".")
            rule_val = match.groups()[1:]
            val = minibelt.get(rslt, *fields)
            if val is None:
                return False
            if rule_type == "equal_rule":
                return str(val) == rule_val[0]
            if rule_type == "greater_rule":
                return float(val) > float(rule_val[0])
            if rule_type == "lesser_rule":
                return float(val) < float(rule_val[0])
            if rule_type == "interval_rule":
                return (float(rule_val[0]) <= float(val)
                        < float(rule_val[1]))
        return


class HttpJsonTimeoutMixin():
    """
    A mixin used to add a verify_timeout func to a
    HttpJsonProbe
    """
    def verify_timeout(self, resp):
        timestamp = resp["response"].get("timestamp")
        if timestamp:
            if not isinstance(timestamp, (int, float)):
                logger.error(
                    "rslt['timestamp'] is not a timestamp(=%r) (probe: %s)",
                    timestamp, self.name)
                return
            ts_now = time.time()
            min_ts = ts_now - (max(self.interval, self.failinterval) * 3)
            if timestamp < min_ts:
                msg = f"OUTDATED (probe_ts {timestamp} < min_ts {min_ts})"
                logger.info("probe %s %s", self.name, msg)
                self.status = "UNKNOWN"
                self.msg = msg + self.msg


class HttpJsonProbeWithTimeout(HttpJsonProbe, HttpJsonTimeoutMixin):
    """
    Same as HttpJsonProbe but check if response has an outdated
    timestamp field
    """

    async def probe_action(self):
        resp = await super().probe_action()
        self.verify_timeout(resp)


class HttpJsonIntervalProbeWithTimeout(HttpJsonIntervalProbe,
                                       HttpJsonTimeoutMixin):
    """Same as HttpJsonProbe but check if response has an outdated
    timestamp field
    """

    async def probe_action(self):
        resp = await super().probe_action()
        self.verify_timeout(resp)
