#!/usr/bin/env python

# #############################################################################
# Copyright : (C) 2023 by MHComm. All rights reserved
#
# __author__ = "Quentin Laymajoux"
# __email__ = "info@mhcomm.fr"
#
# Name       : timon.probes_if
"""
Summary      : functions for interacting with probes

They add for example some caching

"""
# #############################################################################

from minibelt import import_from_path

# cache of probes
probes = {}


def get_probe_cls(cls_name):
    """ cache for probe modules """
    probes[cls_name] = probe = (
        probes.get(cls_name) or import_from_path(cls_name))
    return probe


def mk_probe(cls_name, *args, **kwargs):
    """ creates a probe instance """
    probe = get_probe_cls(cls_name)
    return probe(*args, **kwargs)
