#!/usr/bin/env python
from __future__ import absolute_import, print_function

# #############################################################################
# Copyright : (C) 2017 by Teledomic.eu All rights reserved
#
# Name:         timon.configure
#
# Description:  apply new configuration for timon
#
# #############################################################################

import os
import json
import yaml
import logging
from collections import OrderedDict

logger = logging.getLogger(__name__)

field_order = [
    'type',
    'version',
    'workdir',
    'users',
    'hosts',
    'notifiers',
    'probes',
    'defaults',
    'default_params',
    ]
field_order_dict = dict(( key, val) for val, key in enumerate(field_order))
#print("FOD", sorted(field_order_dict.items(), key=lambda val: field_order_dict[val[0]]))
#print("FOD", field_order_dict)

def apply_config(options):
    """ applies the configuration.

        At the moment this is not much more than
        reading the yaml file, 
        applying defaults and save it as json file
    """

    do_check = options.check
    workdir = options.workdir
    cfgname = os.path.join(workdir, options.fname)

    logger.debug('will read config from %s', cfgname)
    with open(cfgname) as fin:
        cfg = yaml.load(fin)

    logging.info('read config from %s', cfgname)

    # determine workdir from config
    workdir = os.path.realpath(os.path.join(workdir, cfg.get('workdir', '.')))

    logger.debug("workdir: %r", workdir)
    cfg['workdir'] = workdir

    if do_check:
        print("CHECK_CFG")
        return
    
    int_conf_fname = os.path.join(workdir, 'timoncfg_state.json')


    # helps to have a better ordered cfg file for debug
    sort_key_func = lambda kval: (
        field_order_dict.get(kval[0], len(field_order)), 
        kval[0],
        )
    ordered_cfg = OrderedDict(sorted(cfg.items(), key=sort_key_func))

    # dump to file
    with open(int_conf_fname, 'w') as fout:
        json.dump(ordered_cfg, fout, indent=1)

