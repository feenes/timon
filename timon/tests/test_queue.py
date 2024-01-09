#!/usr/bin/env python
"""
#############################################################################
Copyright : (C) 2018 by Teledomic.eu All rights reserved

Name:         timon.test.test_queue

Description:  some unit tests for checking whether queing and especfially
              requeuing works as expected

#############################################################################
"""
import asyncio
import json
import os
from unittest.mock import patch

import timon.configure
import timon.run
import timon.tests.common
from timon.conf.config import TMonConfig
from timon.tests.common import mk_json_mock_load
from timon.tests.common import yaml_mock_load
from timon.tests.helpers import Options
from timon.tests.helpers import Writer


@patch('yaml.safe_load', yaml_mock_load)
def load_cfg(basename, options):
    """ loads config for a test """
    timon.tests.common.yaml_fname = fname = basename + ".yaml"
    options.fname = fname

    with patch('timon.configure.open', Writer, create=True):
        timon.configure.apply_config(options)
        jsontxt = Writer.written_data()

    data = json.loads(jsontxt)

    with patch('json.load', mk_json_mock_load(data)):
        cfg = TMonConfig('/dev/null')
    print(cfg)
    return cfg


async def run_once(options, loop, cfg):
    """ runs one probe iteration cycle """
    rslts = []
    first = True
    for cnt in range(1):
        rslt = await timon.run.run_once(
            options, loop=loop, first=first, cfg=cfg)
        first = False
        print("rslt", rslt)
        rslts.append(rslt)
    await asyncio.sleep(0.1)
    return rslts


def test_01_check_call_order(event_loop):
    """
    find out if notify function was really called
    """
    statefname = "test_state.json"
    if os.path.exists(statefname):
        os.unlink(statefname)
    options = Options(None, statefile=statefname)
    return options  # remove this line when really implementing the test
    # cfg = load_cfg('queue0', options)
    # print(json.dumps(cfg.cfg, indent=1))

    # with (
    #       patch('timon.conf.config.get_config',
    #             lambda options=None: cfg, create=True)
    #       ):
    #     print("EVLOOP", event_loop)
    #     rslts = event_loop.run_until_complete(
    #         run_once(options, event_loop, cfg))
    #     print("rslts", rslts)
