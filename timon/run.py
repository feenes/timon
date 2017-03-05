#!/usr/bin/env python
"""
#############################################################################
Copyright : (C) 2017 by Teledomic.eu All rights reserved

Name:         timon.run

Description:  main tmon runner

#############################################################################
"""

from __future__ import absolute_import, print_function

from timon.config import get_config


def run(options):
    """ runs timon
        :param config: tmon config
        :param init: if True all probes will fire
    """
    print("run tmin")
    print("OPTS:", options)
    cfg = get_config(options=options)
    print("CFG: %r" % cfg)
    state = cfg.get_state()
    print("state", state)
