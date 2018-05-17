#!/usr/bin/env python
"""
#############################################################################
Copyright : (C) 2017 by Teledomic.eu All rights reserved

Name:         timon.test.test_config

Description:  some unit tests for config reader / converter

#############################################################################
"""

import os
import json
from collections import defaultdict
from unittest import TestCase
from unittest.mock import patch, MagicMock

from yaml import safe_load

import timon.configure

from timon.tests.helpers import Options
from timon.tests.helpers import test_data_dir


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

    @classmethod
    def clear_written(cls):
        cls.written.clear()


class ConfigTestCase(TestCase):

    @patch('yaml.safe_load', yaml_mock_load)
    def run_test_for_cfg(self, basename):
        """ read minimal config """
        global yaml_fname
        yaml_fname = fname = basename + ".yaml"
        options = Options(fname)
        # cfg_name = os.path.join(test_data_dir, fname)
        with patch('timon.configure.open', Writer, create=True):
            timon.configure.apply_config(options)

            jsontxt = Writer.written_data()
        data = json.loads(jsontxt)
        print("DATA:\n", data)
        with open('dbg.json', 'w') as fout:
            json.dump(data, fout, indent=1)

        rslt_fname = os.path.join(test_data_dir, basename + ".json")
        with open(rslt_fname) as fin:
            ref_data = json.load(fin)

        ref_data['workdir'] = os.getcwd()
        ref_data['statefile'] = os.path.join(
            os.getcwd(), "timon_state.json")

        for key in ref_data.keys():
            if key in ref_data:
                assert ref_data[key] == data[key]
        Writer.clear_written()

    def test_01_min_cfg(self):
        self.run_test_for_cfg('cfg0')

    def test_02_base_cfg(self):
        self.run_test_for_cfg('cfg1')
