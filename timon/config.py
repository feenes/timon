#!/usr/bin/env python
from __future__ import absolute_import, print_function

# #############################################################################
# Copyright : (C) 2017 by Teledomic.eu All rights reserved
#
# Name:         timon.config
#
# Description:  configuration objects for tmon
#
# #############################################################################

import json

class TMonConfig(object):
    def __init__(self, int_conf_file):
        with open(int_conf_file) as fin:
            self.cfg = data = json.load(fin)


