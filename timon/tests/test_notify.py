#!/usr/bin/env python
"""
#############################################################################
Copyright : (C) 2018 by Teledomic.eu All rights reserved

Name:         timon.test.test_notify

Description:  some unit tests for checking whether notifications  work
              as expected

#############################################################################
"""

import asyncio
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
    """ load's yaml from predefined file instead of
        loading it from passed param
    """
    with open(os.path.join(test_data_dir, yaml_fname)) as fin:
        return safe_load(fin)


def mk_json_mock_load(data):
    """
    mock the json load function to return predefined data
    """
    def loadfunc(fin):
        return data
    return loadfunc


@patch('yaml.safe_load', yaml_mock_load)
def load_cfg(basename, options):
    """ loads config for a test """
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


async def run_once(first, options, loop, cfg):
    """ runs one probe iteration cycle """
    rslt = await timon.run.run_once(options, loop=loop, first=first, cfg=cfg)
    await asyncio.sleep(0.1)
    return rslt


def test_01_check_notif_called(event_loop):
    """
    find out if notify function was really called
    """
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
        print("EVLOOP", event_loop)
        first = True
        for i in range(4):
            print("make_runs", i)
            rslt = event_loop.run_until_complete(
                run_once(first, options, event_loop, cfg))
            print("rslt", rslt)
            first = False
