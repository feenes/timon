#!/usr/bin/env python
"""
#############################################################################
Copyright : (C) 2017 by Teledomic.eu All rights reserved

Name:         timon.configure

Description:  apply new configuration for timon

#############################################################################
"""

from __future__ import absolute_import, print_function

import os
import json
import logging
from collections import OrderedDict

import yaml

logger = logging.getLogger(__name__)


# next two fields just needed for a nice generated json
_orderered_fields = [
    'type',
    'version',
    'workdir',
    'statefile',
    'users',
    'hosts',
    'notifiers',
    'probes',
    'defaults',
    'default_params',
    ]

_field_ord_dict = dict(( key, val) for val, key in enumerate(_orderered_fields))

# needed for knowing which sections to autocomplete
_dict_fields = set(['users', 'hosts', 'notifiers', 'probes'])


def complete_dflt_vals(cfg):
    """ completes default values
        wherever possible
    """
    dflt = cfg['default_params'] # all default params
    for key, entries in cfg.items():
        if key not in _dict_fields:
            continue

        logger.debug("check for %s defaults", key)
        dflts = dflt.get(key, {}) # default params for given section

        #if not dflts:
        #    continue
        logger.info("set defaults for %s", key)
        if dflts:
            logger.debug("defaults %s", dflts)

        for name, entry in sorted(entries.items()):
            logger.debug("%s:%s", key, name)

            if not 'name' in entry:
                entry['name'] = name

            for dkey, dval in dflts.items():
                if not dkey in entry:
                    entry[dkey] = dval

def complete_probes(cfg):
    """ completes all potentially required params for host
        in particular shedules
    """

def setifunset(adict, key, val):
    if not 'key' in adict:
        adict['key'] = val

def complete_hosts(cfg):
    """ completes all potentially required params for host
        in particular (probes, schedule, notify) tuples
    """
    dflt = cfg.get('defaults', {}) # default inst params
    dflt_probes = dflt.get('probes', [])
    dflt_schedule = dflt.get('schedule', None)
    dflt_notifiers = dflt.get('notifiers', [])
    hosts = cfg['hosts']
    for host in hosts.values():
        if not 'probes' in host:
            host['probes'] = list(dict(probe=val) for val in dflt_probes)
        for probe in host['probes']:
            assert isinstance(probe, dict)
            if not 'name' in probe:
                probe['name'] = host['name'] + "_" + probe['probe']
            if not 'schedule' in probe:
                probe['schedule'] = dflt_schedule
            if not 'notifiers' in probe:
                probe['notifiers'] = list(dflt_notifiers)


def order_cfg(cfg):
    """ order config dict such, that
        generated output is 'better' ordered for debug
    """
    # helps to have a better ordered cfg file for debug
    sort_key_func = lambda kval: (
        _field_ord_dict.get(kval[0], len(_field_ord_dict)),
        kval[0],
        )
    ordered_cfg = OrderedDict(sorted(cfg.items(), key=sort_key_func))
    return ordered_cfg


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

    statefile = os.path.join(workdir, cfg.get('statefile', 'timon_state.json'))
    cfg['statefile'] = statefile

    if do_check:
        print("CHECK_CFG")
        return

    # set abspath for work dir
    int_conf_fname = os.path.join(workdir, 'timoncfg_state.json')

    complete_dflt_vals(cfg)
    complete_probes(cfg)
    complete_hosts(cfg)

    cfg = order_cfg(cfg)

    # dump to file
    with open(int_conf_fname, 'w') as fout:
        json.dump(cfg, fout, indent=1)


