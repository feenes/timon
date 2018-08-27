#!/usr/bin/env python
"""
# #############################################################################
# Copyright : (C) 2017 by Teledomic.eu All rights reserved
#
# Name:         timon.config
#
# Description:  configuration objects for tmon
#
# #############################################################################
"""

from __future__ import absolute_import, print_function

import json
import logging
import os

import minibelt

logger = logging.getLogger()

configs = {}  # cache for configs


class TMonConfig(object):
    """ config object
    """
    # CHECK whether pickle doesn't load faster.
    # at 2011 it seems json was faster. have to try for our scenario
    # but it's not that high priority
    def __init__(self, int_conf_file):
        """ creates config from a config file
            At the moment this is json, might switch
            to pickle later.
        """
        self.fname = int_conf_file
        with open(int_conf_file) as fin:
            self.cfg = cfg = json.load(fin)
        self.probes = cfg['all_probes']
        self.state = None
        self.queue = None
        self.notifiers = {}
        self.notif_cfg = cfg['notifiers']
        self.users = users = cfg.get('users') or {}
        for name, userinfo in users.items():
            if 'name' not in userinfo:
                userinfo['name'] = name

    def get_state(self):
        """ gets current state of timon
            currently a json file might be pickle lateron
        """
        if self.state:
            return self.state

        from timon.state import TMonState
        self.state = state = TMonState(self.cfg['statefile'], config=self)
        return state

    def get_probes(self):
        """ generator for all probes """
        # TODO: might create a cached list of objects
        # TODO: instead of returning the simple json dict
        for probe in self.probes.values():
            yield probe

    def get_notifier(self, name):
        notifier = self.notifiers.get(name)
        if notifier:
            return notifier
        from timon.notifiers import mk_notifier
        notif_cfg = dict(self.notif_cfg[name])
        notif_cls = notif_cfg['cls']
        if 'users' in notif_cfg:
            usernames = notif_cfg['users']
            notif_cfg['users'] = [self.users[name] for name in usernames]
        notifier = self.notifiers[name] = mk_notifier(notif_cls, **notif_cfg)
        return notifier

    def get_queue(self):
        """ gets queue or update from state """
        if self.queue is not None:
            return self.queue
        state = self.get_state()
        self.queue = state.get_queue()
        # print("IQ", self.queue)
        return self.queue

    def refresh_queue(self):
        """ refreshes / updates queue from new config """
        state = self.get_state()
        return state.refresh_queue()

    def save_state(self, safe=True):
        """ saves queue to state
            :param safe: bool. If true file will be safely written.
                            This means.w ritten to a temp file, being closed
                            and renamed. this another process reading will
                            never see a partial file
        """
        self.state.save(safe=safe)

    def mk_sched_entry(self, name, t_next=None, interval=None,
                       failinterval=None, schedule=None):
        return self.state.mk_sched_entry(
                name,
                t_next=t_next,
                interval=interval,
                schedule=schedule,
                )

    def get_plugin_param(self, name, default=None):
        return minibelt.get(
            self.cfg, 'plugins', *(name.split('.')), default=default)

    def __repr__(self):
        return "TMonConfig<%s>" % self.fname


def get_config(fname=None, options=None, reload=False):
    """ gets config from fname or options
        uses a cached version per filename except reload = True
        :param fname: path of timon config
        :param reload: if true reloading / recompiling config will be forced
    """
    # print("GCFG", fname, options)
    if fname is None:
        norm_fname = None
    else:
        norm_fname = os.path.realpath(fname)

    # print("NFP", norm_fname)
    config = configs.get(norm_fname) if not reload else None

    if config:
        return config
    # print("NO CFG for ", norm_fname, "got only", configs.keys())

    workdir = options.workdir
    if fname is None:
        norm_fname = os.path.join(workdir, options.compiled_config)

    cfgname = os.path.join(workdir, options.fname)

    # get timestamps of compiled cfg and src cfg
    t_src = os.path.getmtime(cfgname)
    if os.path.isfile(norm_fname):
        t_cmp = os.path.getmtime(norm_fname)
    else:
        t_cmp = t_src - 1  # just any time older than src

    if t_cmp < t_src:  # is src newer than compiled cfg
        from timon.configure import apply_config
        options.check = False
        apply_config(options)
    config = TMonConfig(norm_fname)
    configs[fname] = config
    if norm_fname is None:
        configs[None] = config

    return config
