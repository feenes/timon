#!/usr/bin/env python
"""
# #############################################################################
# Copyright : (C) 2017 by Teledomic.eu All rights reserved
#
# Name:         timon.state
#
# Description:  state object for timon
#
# #############################################################################
"""

from __future__ import absolute_import, print_function

import json
import heapq
import logging
import time
from heapq import heappush
from heapq import heapreplace
from heapq import heappop

logger = logging.getLogger(__name__)

class TMonQueue(object):
    def __init__(self, state):
        self.heap = []
        self.state = state # just in case
        self.probes = state.probes
        self.sched_dict = {}
        cfg = self.state.state['task_queue']
        self.probes = self.state.probes # TODO: really a copy here?
        self.sched_dict = cfg['sched_dict']
        self.heap[:] = cfg['heap']
        print(self.probes)

    def add(self, sched_entry):
        """ adds an entry to the scheduler """
        name = sched_entry['name']
        logger.debug("Entry[%s] = %s", name, sched_entry)
        self.sched_dict[name] = sched_entry
        heappush(self.heap, [sched_entry['t_next'], name])

    def pop(self):
        """ gets an entry from the scheduler """
        t, sched_entry = heappop(self.heap)
        sched = self.sched_dict.pop(sched_entry)
        return t, sched

    def add_get(self, push_entry):
        """ adds entry to scheduler and gets one """
        rslt = t, sched_entry = heappop(self.heap)
        sched = self.sched_dict.pop(sched_entry)
        t, sched_entry = push_entry
        t, sched_entry = heapreplace(self.heap, push_entry)
        self.sched_dict[sched_entry] = sched_entry

        
    def get_expired(self, t_exp, do_pop=True):
        if do_pop: # caller just as to push new values
            while True:
                t, probe_id = self.heap[0]
                if t > t_exp:
                    return
                yield self.pop()
        else: # yield. caller must pop/push
            while True:
                t, probe_id = self.heap[0]
                if t > t_exp:
                    return
                to_push = yield t, probe_id

    def get_probes(self, now=None):
        from .probe_if import mk_probe
        now = now if now else time.time()
        heap = self.heap
        pop = self.pop
        all_probes = self.probes
        while True:
            if not heap or (heap[0][0] > now):
                if heap:
                    print("H0",heap[0], "aborting")
                break
            print("H0",heap[0])
            _t, entry = pop()
            print("E", entry)
            entry_name = entry["name"]
            probe_args = all_probes[entry_name]
            cls_name = probe_args['cls']
            print("CNAME", cls_name)
            probe = mk_probe(cls_name, entry_name)
            yield probe
        

    def __repr__(self):
        return "TMonQ<%d probes / %d entries/ %d in heap>" % (
            len(self.probes), len(self.sched_dict), len(self.heap))

    def __contains__(self, item):
        return item in self.sched_dict

    def is_empty(self):
        return not self.heap

    #def __iter__(self):
    #    """ requires a sort but iterates in order """
    #    for t, probe_id in sorted(self.heap):
    #        yield t, self.sched_dict[probe_id]
    
    def items(self):
        for value in self.sched_dict.items():
            yield value

    def as_dict(self):
        """ returns queue as a jsonable list """
        rslt = dict(heap=self.heap,  sched_dict=self.sched_dict)
        return rslt


class TMonState(object):
    """ keeps track of timon's state
        like schedulers / etc
    """
    def __init__(self, state_file=None, config=None):
        self.fname = fname = state_file
        self.config = config
        self.probes = config.probes
        self.queue = None
        self.state = {}
        try:
            with open(fname) as fin:
                self.state = json.load(fin)
        except FileNotFoundError:
            self.reset_state()
            self.save()

    def get_queue(self):
        """ gets queue or update from state """
        if self.queue is not None:
            return self.queue
        self.queue = TMonQueue(self)
        return self.queue

    def save(self):
        """ saves state to file """
        logger.debug("Shall save state to %s", self.fname)
        with open(self.fname, "w") as fout:
            if self.queue is not None:
                self.state['task_queue'] = self.queue.as_dict()
            else:
                self.state['task_queue'] = dict(heap=[], sched_dict={})
            json.dump(self.state, fout, indent=1)

    def reset_state(self):
        """ create a completely new fresh state """
        self.state = dict(
            type="timon_state",
            version="0.0.1",
            task_queue=[],
        )

