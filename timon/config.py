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

import os
import json
import time
from itertools import count
from collections import OrderedDict
import logging

logger = logging.getLogger()

configs = {} # cache for configs


class TMonConfig(object):
    """ config object 
    """
    # CHECK if pickle doesn't load faster
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
        """ get all probes and create a cached list """
        for probe in self.probes.values():
            yield probe

    def get_queue(self):
        """ gets queue or update from state """
        if self.queue is not None:
            return self.queue
        from timon.state import TMonQueue
        state = self.get_state()
        self.queue = queue = state.get_queue()
        #print("IQ", queue)
        return self.queue

    def refresh_queue(self):
        """ refreshes / updates queue from new config """
        #print("REF Q")
        now_s = time.time()
        state = self.get_state()
        queue = self.queue = self.get_queue()
        for probe in self.get_probes():
            name = probe['name']
            if not name in queue:
                logger.debug("Adding entry for %s", name)
                sched = self.cfg['schedules'][probe['schedule']]
                sched_st = self.mk_sched_entry(
                    probe['name'],
                    t_next=now_s,
                    schedule=sched,
                    )
                queue.add(sched_st)
        #print("Q: ", self.queue)
        s_queue = OrderedDict()
        for key, val in sorted(queue.items(), 
                key=lambda key_val: (key_val[1]['t_next'], key_val[1]['interval'])):
            s_queue[key] = val
        self.queue = s_queue
        #print("SQ: ", s_queue)

    def save_state(self, safe=True):
        """ saves queue to state 
            :param safe: bool. If true file will be safely written.
                            This means.w ritten to a temp file, being closed and
                            renamed. this another process reading will never see
                            a partial file
        """
        self.state.save(safe=safe)

    @staticmethod
    def mk_sched_entry(name, t_next=None, interval=None, 
            failinterval=None, schedule=None):
        schedule = schedule or {}
        t_next = t_next or time.time()
        interval = interval or schedule.get('interval', 901)
        failinterval = failinterval or schedule.get('failinterval', 901)
        return dict(
            name=name,
            t_next=t_next,
            interval=interval,
            failinterval=failinterval,
            )

    def __repr__(self):
        return "TMonConfig<%s>" % self.fname

def get_config(fname=None, options=None, reload=False):
    """ gets config from fname or options
        uses a cached version per filename except reload = True
    """
    #print("GCFG", fname, options)

    if fname is None:
        norm_fname = None
    else:
        norm_fname = os.path.realpath(fname)
    
    config = configs.get(norm_fname) if not reload else None
    
    if config:
        return config
    #print("NO CFG for ", norm_fname, "got only", configs.keys())

    if fname is None:
        workdir = options.workdir
        norm_fname = os.path.join(workdir, options.compiled_config)

    config = TMonConfig(norm_fname)
    configs[fname] = config
    if norm_fname is None:
        configs[None] = config

    return config

