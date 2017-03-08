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
from uuid import uuid4
from collections import OrderedDict
from itertools import count

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
                logger.debug("NAME = %r", name)
                entry['name'] = name

            for dkey, dval in dflts.items():
                if not dkey in entry:
                    entry[dkey] = dval
                    logger.debug("%r = %r", dkey, dval)


def complete_schedules(cfg):
    """ add name to each schedule """
    for name, schedule in cfg['schedules'].items():
        schedule['name'] = name


def complete_probes(cfg):
    """ add all default values to probes if no specific val is set """
    dflt = cfg['default_params'].get('probes', {})
    for probe_name, probe in cfg['probes'].items():
        if not 'probe' in probe:
            probe['probe'] = probe_name
        for key, val in dflt.items():
            if not key in probe:
                probe[key] = val


def complete_hosts(cfg):
    """ completes all potentially required params for host
        in particular (probes, schedule, notify) tuples
    """
    dflt = cfg.get('defaults', {}) # default inst params
    dflt_probes = dflt.get('probes', [])
    dflt_schedule = dflt.get('schedule', None)
    dflt_notifiers = dflt.get('notifiers', [])
    probes = dict(cfg['probes'])
    hosts = cfg['hosts']
    schedules = cfg['schedules']
    for host in hosts.values():
        if not 'probes' in host:
            host['probes'] = list(dict(probe=probe) for probe in dflt_probes)
            logger.debug("no probes specified for host %s. will use %r",
                host['name'], host['probes'])

        hprobes = host['probes']

        if type(hprobes) in (str,): # if only one probe conv to list of one
            hprobes = [ hprobes ]

        # if just names were include convert to dict
        #logger.debug("probes[%s]: %r", host['name'], hprobes)
        hprobes = [ dict(probes[probe]) if type(probe) in (str,) 
            else probe for probe in hprobes ]
        #logger.debug("probes[%s]: %r", host['name'], hprobes)
    
        # set unique name + add default values for non existing keys
        for probe in hprobes:
            assert isinstance(probe, dict)
            probe_name = probe['name'] = host['name'] + "_" + probe['probe']
            updated_probe = dict(probes[probe['probe']])
            updated_probe.update(probe)
            probe.update(updated_probe)
        logger.debug("probes[%s]: %r", host['name'], hprobes)


        host['probes'] = hprobes


def mk_all_probes(cfg):
    """ add unique id (counter) to all probes
    """
    ctr = count()
    cfg['all_probes'] = all_probes = OrderedDict()
    for host_name, host in cfg['hosts'].items():
        host_probes = host['probes']
        host['probes'] = [ probe['name'] for probe in host_probes ]
        for probe in host_probes:
            #probe['uuid'] = str(uuid4()) # perhaps useful,
                                          # but probably name is sufficient
            #probe['idx'] = next(ctr) # not really needed
            probe['host'] = host_name
            all_probes[probe['name']] = probe


def setifunset(adict, key, val):
    if not 'key' in adict:
        adict['key'] = val


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
    complete_schedules(cfg)
    complete_probes(cfg) # default probes
    complete_hosts(cfg)
    
    mk_all_probes(cfg)

    cfg = order_cfg(cfg)

    # dump to file
    with open(int_conf_fname, 'w') as fout:
        json.dump(cfg, fout, indent=1)


