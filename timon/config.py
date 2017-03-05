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

class TMonConfig(object):
    def __init__(self, int_conf_file):
        self.fname = int_conf_file
        with open(int_conf_file) as fin:
            self.cfg = data = json.load(fin)
        self.state = None

    def get_state(self):
        if self.state:
            return self.state

        from timon.state import TMonState
        return TMonState(self.cfg['statefile'])

    def __repr__(self):
        return "TMonConfig<%s>" % self.fname

def get_config(fname=None, options=None):
    """ gets config from fname or options """
    if fname:
        return TMonConfig(fname)
    else:
        workdir = options.workdir
        fname = os.path.join(workdir, options.compiled_config)
        return TMonConfig(fname)

