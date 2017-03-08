#!/usr/bin/env python
"""
#############################################################################
Copyright : (C) 2017 by Teledomic.eu All rights reserved

Name:         timon.run

Description:  main tmon runner

#############################################################################
"""

from __future__ import absolute_import, print_function

import logging

from timon.config import get_config


logger = logging.getLogger(__name__)


def run(options):
    # IMPLEMENT PARAMS/OPTIONS or remove doc string
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
    queue = cfg.get_queue()
    print("IQ", queue)
    cfg.refresh_queue() # add any not refreshed entries to queue


    print("IR")
    from .runner import Runner

    # get all queue entries less than a certain time stamp
    probes = queue.get_probes()
    for probe in probes:
        print("P:", probe)

    exit(0)
    # get status mods on demand from cfg (mod_names / dict cache)
    # get notify mods on demand from cfg (mod_names / dict cache)
    # run probes

    print("IQ", queue)
    cfg.save_state()
    
