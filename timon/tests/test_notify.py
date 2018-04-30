#!/usr/bin/env python

import json
import os

from unittest.mock import patch
from yaml import safe_load

import timon.run
from timon.tests.helpers import Options
from timon.tests.helpers import Writer
from timon.tests.helpers import test_data_dir

import timon.configure
from timon.config import TMonConfig


yaml_fname = None


# TODO: move to timon.tests.common?
def yaml_mock_load(fin):
    with open(os.path.join(test_data_dir, yaml_fname)) as fin:
        return safe_load(fin)


# return a function returning
def mk_json_mock_load(data):
    def loadfunc(fin):
        return data
    return loadfunc


@patch('yaml.safe_load', yaml_mock_load)
def load_cfg(basename, options):
    global yaml_fname
    yaml_fname = fname = basename + ".yaml"
    options.fname = fname

    with patch('timon.configure.open', Writer, create=True):
        timon.configure.apply_config(options)
        jsontxt = Writer.written_data()

    data = json.loads(jsontxt)

    with patch('json.load', mk_json_mock_load(data)):
        cfg = TMonConfig('/dev/null')
    print(cfg)
    return cfg


def test_01_min_cfg(event_loop):
    statefname = "test_state.json"
    if os.path.exists(statefname):
        os.unlink(statefname)
    options = Options(None, statefile=statefname)
    cfg = load_cfg('notif0', options)
    print(json.dumps(cfg.cfg, indent=1))
    with (
            patch('timon.config.get_config',
                  lambda options=None: cfg, create=True)
            ):
        timon.run.run(options)
