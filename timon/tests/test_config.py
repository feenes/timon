#!/usr/bin/env python
"""
#############################################################################
Copyright : (C) 2017 by Teledomic.eu All rights reserved

Name:         timon.test.test_config

Description:  some unit tests for config reader / converter

#############################################################################
"""

from __future__ import absolute_import, print_function

import os
import json
from collections import defaultdict
from unittest import TestCase
from unittest.mock import patch, MagicMock

from yaml import safe_load

import timon.configure


mod_dir = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))
test_data_dir = os.path.join(mod_dir, 'data', 'test')


class Options:
    """ options for testing """
    def __init__(self, fname):
        self.check = False
        self.workdir = ""
        self.fname = fname


yaml_fname = None


def yaml_mock_load(fin):
    with open(os.path.join(test_data_dir, yaml_fname)) as fin:
        return safe_load(fin)


class Writer(MagicMock):
    written = defaultdict(list)

    def __init__(self, *args, **kwargs):
        fname = args[0]
        super().__init__(*args, **kwargs)
        self.fname = fname

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        pass

    @classmethod
    def written_data(cls, fname=None):
        if fname is None:
            fnames = list(cls.written.keys())
            fname = fnames[0]
        return "".join(cls.written[fname])

    def write(self, data):
        self.written[self.fname].append(data)


class ConfigTestCase(TestCase):

    @patch('yaml.safe_load', yaml_mock_load)
    def test_min_cfg(self):
        """ read minimal config """
        global yaml_fname
        yaml_fname = fname = "cfg0.yaml"
        options = Options(fname)
        # cfg_name = os.path.join(test_data_dir, fname)
        with patch('timon.configure.open', Writer, create=True):
            timon.configure.apply_config(options)

            self.assertEqual(1, 1)
            jsontxt = Writer.written_data()
            data = json.loads(jsontxt)
            with open('dbg.json', 'w') as fout:
                json.dump(data, fout, indent=1)

        rslt_fname = os.path.join(test_data_dir, "cfg0.json")
        with open(rslt_fname) as fin:
            json.load(fin)
