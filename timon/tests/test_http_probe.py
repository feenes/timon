#!/usr/bin/env python
"""
#############################################################################
Copyright : (C) 2022 by Teledomic.eu All rights reserved

Name:         timon.test.test_html_probe

Description:  some unit tests for checking parts of an http probe

#############################################################################
"""

import json
from pathlib import Path
from unittest.mock import patch

from timon.config import TMonConfig
from timon.probes import HttpJsonIntervalProbe
from timon.probes import HttpJsonProbe
from timon.probes import HttpProbe
from timon.probes import Probe
from timon.tests.common import yaml_mock_load

# ###########################################################
# TODO: make real tests for http probe (httpx mock)
# ###########################################################

def mk_dflt_args():
    """
    create default args for probe creation
    """
    return dict(
            name="probe1",
            host="srv1",
            workdir=".",
            t_next=None,
            interval=120,
            failinterval=60,
        )


def get_test_config():
    """
    create timon config for tests
    """
    cfg_file = Path(__file__).parent.parent / "data" / "test" / "cfg1.json"
    cfg = TMonConfig(cfg_file)
    return cfg


def mk_http_probe_result():
    return dict(
        response=dict(
            value=5,
            ),
        reason=None,
        status=200,
        )


def test_base_probe():
    """
    just instantiate a probe and see it doesn't fail
    """
    kwargs = dict(mk_dflt_args())
    kwargs.update(
        dict(
            )
        )
    Probe(**kwargs)


@patch('yaml.safe_load', yaml_mock_load)
@patch('timon.probes.get_config', get_test_config)
def test_simple_url():
    """
    check that simple urls derived from host names are passed
    """
    kwargs = dict(mk_dflt_args())
    probe = HttpProbe(**kwargs)
    assert "https://hn1:443/" == probe.url


@patch('yaml.safe_load', yaml_mock_load)
@patch('timon.probes.get_config', get_test_config)
def test_url_w_args():
    """
    check that url_params are properly handled
    """
    kwargs = dict(mk_dflt_args())
    kwargs.update(
        dict(
            url="https://myurl/%s/%s",
            url_params=["one", "two"]
            )
        )
    probe = HttpProbe(**kwargs)
    assert "https://myurl/one/two" == probe.url


@patch('yaml.safe_load', yaml_mock_load)
@patch('timon.probes.get_config', get_test_config)
def test_json_probe():
    """
    basic tests for HttpJsonProbe
    """
    kwargs = dict(mk_dflt_args())
    kwargs.update(
        dict(
            ok_rule="response.value:5",
            warning_rule="response.value:6",
            error_rule="response.value:7",
            )
        )
    probe = HttpJsonProbe(**dict(kwargs))
    rslt = mk_http_probe_result()
    probe.parse_result(rslt)
    assert probe.status == "OK"

    rslt["response"]["value"] = 6
    probe.parse_result(rslt)
    assert probe.status == "WARNING"

    rslt["response"]["value"] = 7
    probe.parse_result(rslt)
    assert probe.status == "ERROR"

    rslt["response"]["value"] = 8
    probe.parse_result(rslt)
    assert probe.status == "UNKNOWN"

    rslt["response"]["value"] = 1
    kwargs["ok_rule"] = None
    kwargs["error_rule"] = "DEFAULT"
    probe = HttpJsonProbe(**dict(kwargs))
    probe.parse_result(rslt)
    assert probe.status == "ERROR"

    rslt["response"]["value"] = 6
    probe.parse_result(rslt)
    assert probe.status == "WARNING"


@patch('yaml.safe_load', yaml_mock_load)
@patch('timon.probes.get_config', get_test_config)
def test_json_interval_probe():
    """
    basic tests for HttpJsonIntervalProbe
    """
    kwargs = dict(mk_dflt_args())
    kwargs.update(
        dict(
            ok_rule="response.value:5",
            warning_rule="response.value=6",
            error_rule="response.value>8",
            )
        )
    probe = HttpJsonIntervalProbe(**kwargs)
    rslt = mk_http_probe_result()
    rslt["response"]["value"] = 5
    probe.parse_result(rslt)
    assert probe.status == "OK"

    rslt["response"]["value"] = 6
    probe.parse_result(rslt)
    assert probe.status == "WARNING"

    rslt["response"]["value"] = 8
    probe.parse_result(rslt)
    assert probe.status == "UNKNOWN"

    rslt["response"]["value"] = 9
    probe.parse_result(rslt)
    assert probe.status == "ERROR"

    kwargs = dict(mk_dflt_args())
    kwargs.update(
        dict(
            ok_rule="response.value<5",
            warning_rule="response.value=[6,9]",
            )
        )
    probe = HttpJsonIntervalProbe(**kwargs)

    rslt["response"]["value"] = 4
    probe.parse_result(rslt)
    assert probe.status == "OK"

    rslt["response"]["value"] = 6
    probe.parse_result(rslt)
    assert probe.status == "WARNING"

    rslt["response"]["value"] = 8
    probe.parse_result(rslt)
    assert probe.status == "WARNING"

    rslt["response"]["value"] = 9
    probe.parse_result(rslt)
    assert probe.status == "ERROR"

    rslt["response"]["value"] = 5
    probe.parse_result(rslt)
    assert probe.status == "ERROR"

    kwargs = dict(mk_dflt_args())
    kwargs.update(
        dict(
            ok_rule="response.value<5",
            warning_rule="response.value=[6,9]",
            error_rule=None,
            )
        )
    probe = HttpJsonIntervalProbe(**kwargs)

    rslt["response"]["value"] = 4
    probe.parse_result(rslt)
    assert probe.status == "OK"

    rslt["response"]["value"] = 6
    probe.parse_result(rslt)
    assert probe.status == "WARNING"

    rslt["response"]["value"] = 8
    probe.parse_result(rslt)
    assert probe.status == "WARNING"

    rslt["response"]["value"] = 9
    probe.parse_result(rslt)
    assert probe.status == "UNKNOWN"

    rslt["response"]["value"] = 5
    probe.parse_result(rslt)
    assert probe.status == "UNKNOWN"
