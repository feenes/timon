"""
#############################################################################
Copyright : (C) 2022 by Teledomic.eu All rights reserved

Name:         timon.test.common

Description:  some common helpers for timon tests

#############################################################################
"""

from yaml import safe_load

from timon.tests.helpers import test_data_path

yaml_fname = None


def yaml_mock_load(fin):
    """ load's yaml from predefined file instead of
        loading it from passed param
    """
    fname = test_data_path / yaml_fname
    print(f"MOCK LOAD {fname}")

    with open(fname) as fin:
        return safe_load(fin)


def mk_json_mock_load(data):
    """
    mock the json load function to return predefined data
    """
    def loadfunc(fin):
        return data

    return loadfunc
