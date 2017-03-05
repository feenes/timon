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

class TMonState(object):
    """ keeps track of timon's state
        like schedulers / etc
    """
    def __init__(self, state_file=None):
        self.fname = fname = state_file
        try:
            with open(fname) as fin:
                self.state = json.load(fin)
        except FileNotFoundError:
            self.reset_state()
            self.save_state()

    def save_state(self):
        """ saves state to file """
        with open(self.fname, "w") as fout:
            json.dump(self.state, fout, indent=1)

    def reset_state(self):
        """ create a completely new fresh state """
        self. state = dict(
            type="timon_state",
            version="0.0.1",
            task_queue=[],
        )



