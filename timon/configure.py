#!/usr/bin/env python
"""
#############################################################################
Copyright : (C) 2017 by Teledomic.eu All rights reserved

Name:         timon.configure

Description:  apply new configuration for timon

#############################################################################
"""

from __future__ import absolute_import, print_function

import json
import logging
import os

from collections import OrderedDict

import yaml

from timon.conf.grpby import cnvt_grpby_to_nested_dict
from timon.conf.grpby import cnvt_nested_grpby_to_lst_dict


logger = logging.getLogger(__name__)


# next two vars needed for ordering generated json
# order in which fields shall show up in json
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
    'host_groups',
    ]

_field_ord_dict = dict(
        (key, val) for val, key in enumerate(_orderered_fields))

# needed for knowing which sections to autocomplete
_dict_fields = set(['users', 'hosts', 'notifiers', 'probes'])


class ConfigError(Exception):
    """ custom exception """


def mk_cert_info(cert_info):
    """ 'normalizes' cert info
        if a None or a tuple / list has been passed return unchanged.

        if a string is passed treat it as a filename of a crt file.
            - if a corresponding file with a .key suffix exists treat it
              as a key file
            - otherwise assume that crt file contains also the key
    """
    if not type(cert_info) in (bytes, str):
        return cert_info
    else:
        crt_fname = cert_info
        root, ext = os.path.splitext(crt_fname)
        key_fname = root + '.key'
        if not os.path.isfile(key_fname):
            key_fname = crt_fname
        if not os.path.isfile(crt_fname) or not os.path.isfile(key_fname):
            if key_fname == crt_fname:
                raise ConfigError("Cert file %r doesn't exist" % crt_fname)
            raise ConfigError("Cert file %r or key file %r doesn't exist"
                              % (crt_fname, key_fname))
        if key_fname == crt_fname:
            return crt_fname
        else:
            return (crt_fname, key_fname)


def complete_dflt_vals(cfg):
    """ completes default values for each section, that
        can be found in _dict_fields
        just one level / default vals
    """
    dflt = cfg['default_params']  # all default params
    for key, entries in cfg.items():
        if key not in _dict_fields:
            continue

        logger.debug("check for %s defaults", key)
        dflts = dflt.get(key, {})  # default params for given section

        # if not dflts:
        #     continue
        logger.info("set defaults for %s", key)
        if dflts:
            logger.debug("defaults %s", dflts)

        for name, entry in sorted(entries.items()):
            logger.debug("%s:%s", key, name)

            if 'name' not in entry:  # set name field if missing
                logger.debug("NAME = %r", name)
                entry['name'] = name

            for dkey, dval in dflts.items():
                if dkey not in entry:
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
        if 'probe' not in probe:
            probe['probe'] = probe_name
        for key, val in dflt.items():
            if key not in probe:
                probe[key] = val


def complete_hosts(cfg):
    """ completes all potentially required params for host
        in particular (probes, schedule, notify) tuples
        creates also probe instances
    """
    dflt = cfg.get('defaults', {})  # default inst params
    dflt_probes = dflt.get('probes', [])
    # dflt_schedule = dflt.get('schedule', None)
    # dflt_notifiers = dflt.get('notifiers', [])
    probes = dict(cfg['probes'])
    hosts = cfg['hosts']
    # schedules = cfg['schedules']
    for host in hosts.values():
        if 'probes' not in host:
            host['probes'] = list(dict(probe=probe) for probe in dflt_probes)
            logger.debug("no probes specified for host %s. will use %r",
                         host['name'], host['probes'])

        hprobes = host['probes']

        if type(hprobes) in (str,):  # if only one probe conv to list of one
            hprobes = [hprobes]

        # if just names were include convert to dict
        # logger.debug("probes[%s]: %r", host['name'], hprobes)
        hprobes = [dict(probes[probe]) if type(probe) in (str,)
                   else probe for probe in hprobes]
        # logger.debug("probes[%s]: %r", host['name'], hprobes)

        # set unique name + add default values for non existing keys
        host_probe_params = host.get('probe_params') or {}
        for probe in hprobes:
            assert isinstance(probe, dict)
            probe_name = probe['probe']
            probe['name'] = host['name'] + "_" + probe_name
            updated_probe = dict(probes[probe_name])
            updated_probe.update(probe)
            probe.update(updated_probe)
            probe_params = host_probe_params.get(probe_name) or {}
            probe.update(probe_params)
        logger.debug("probes[%s]: %r", host['name'], hprobes)

        host['probes'] = hprobes

        if 'client_cert' not in host:
            host['client_cert'] = None
        else:
            host['client_cert'] = mk_cert_info(host['client_cert'])


def mk_all_probes(cfg):
    """ add unique id (counter) to all probes
    """
    cfg['all_probes'] = all_probes = OrderedDict()
    for host_name, host in sorted(cfg['hosts'].items()):
        host_probes = host['probes']
        # print(host_probes)
        host['probes'] = [probe['name'] for probe in host_probes]
        for probe in host_probes:
            probe['host'] = host_name
            all_probes[probe['name']] = probe


# TODO: remove: function seens used nowhere
def __setifunset(adict, key, val):
    """ sets value in dict if not set so far """
    if 'key' not in adict:
        adict['key'] = val


def mk_ordered_dict(adict):
    """ convert a dict instance to an ordered dict
        ordered by key
    """
    rslt = OrderedDict()
    for key, val in sorted(adict.items()):
        if isinstance(val, dict):
            val = mk_ordered_dict(val)
        rslt[key] = val
    return rslt


def order_cfg(cfg):
    """ order config dict such, that generated cfg file
        is predictively ordered
    """

    # sort lower levels of cfg file by keys
    for key, val in cfg.items():
        if isinstance(val, dict):
            cfg[key] = mk_ordered_dict(val)

    # a nicer top level order for the cfg file for simpler debugging
    def sort_key_func(kval):
        return (
            _field_ord_dict.get(kval[0], len(_field_ord_dict)),
            kval[0],
            )
    ordered_cfg = OrderedDict(sorted(cfg.items(), key=sort_key_func))

    return ordered_cfg


def apply_config(options):
    """ applies the configuration.

        This is not much more than reading the yaml file,
        applying defaults and save it as json file
        However timon.config will have a config file, which is more
        uniform than the human written config file. Many default values
        are explicitely set and hopefully, this will accelerate and
        simplify the run code as it has to handle less
        exceptions / fallbacks to defaults
    """

    do_check = options.check
    workdir = options.workdir
    cfgname = os.path.join(workdir, options.fname)

    logger.debug('starting to read config from %s', cfgname)
    with open(cfgname) as fin:
        cfg = yaml.safe_load(fin)

    logging.info('read config from %s', cfgname)

    # determine workdir from config
    workdir = os.path.realpath(os.path.join(workdir, cfg.get('workdir', '.')))

    logger.debug("workdir: %r", workdir)
    cfg['workdir'] = workdir

    statefile = os.path.join(workdir, cfg.get('statefile', 'timon_state.json'))
    cfg['statefile'] = options.statefile or statefile
    if do_check:
        print("CHECK_CFG not implemented so far")
        return
    if "webif" in cfg:
        if "group_by" in cfg["webif"]:
            rslt = cnvt_grpby_to_nested_dict(
                cfg["webif"]["group_by"], cfg["hosts"])
            rslt = cnvt_nested_grpby_to_lst_dict(
                rslt, cfg["webif"]["group_by"])
            cfg["host_group"] = rslt
    # set abspath for work dir
    int_conf_fname = os.path.join(workdir, 'timoncfg_state.json')
    complete_dflt_vals(cfg)
    complete_schedules(cfg)
    complete_probes(cfg)  # default probes
    complete_hosts(cfg)

    mk_all_probes(cfg)

    cfg = order_cfg(cfg)

    # dump to file
    with open(int_conf_fname, 'w') as fout:
        json.dump(cfg, fout, indent=1)
