#!/usr/bin/env python
"""
#############################################################################
Name:         timon.tests.test_log_confs

Description:  tests for timon's log configurations (timon.log_confs)

#############################################################################
"""
import json
import logging
import logging.config

import pytest
import yaml

import timon.log_confs.default as default
import timon.log_confs.dict as dict_conf

LOADERS = {
    ".json": json.load,
    ".yaml": yaml.safe_load,
    ".yml": yaml.safe_load,
}


@pytest.fixture
def restore_logging():
    """
    dictConfig() changes global logging state. Restore what it touches.
    """
    names = [""] + list(default.get_log_settings()["loggers"])
    loggers = [logging.getLogger(name) for name in names]
    saved = [
        (lgr, lgr.handlers[:], lgr.level, lgr.propagate, lgr.disabled)
        for lgr in loggers]
    yield
    for lgr, handlers, level, propagate, disabled in saved:
        lgr.handlers[:] = handlers
        lgr.setLevel(level)
        lgr.propagate = propagate
        lgr.disabled = disabled


def test_default_settings_are_valid(restore_logging):
    settings = default.get_log_settings(level="WARNING")
    assert isinstance(settings, dict)
    handler_names = set(settings["handlers"])
    for name, logger_cfg in settings["loggers"].items():
        handlers = logger_cfg.get("handlers", [])
        assert isinstance(handlers, list), name
        assert set(handlers) <= handler_names, name
    logging.config.dictConfig(settings)


@pytest.mark.parametrize("suffix", [".json", ".yaml", ".yml"])
def test_dict_creates_missing_file(tmp_path, suffix):
    path = tmp_path / f"log_config{suffix}"
    settings = dict_conf.get_log_settings(file=str(path), level="WARNING")
    assert path.exists()
    with path.open() as fin:
        assert LOADERS[suffix](fin) == settings
    if suffix != ".json":
        # shared objects must be written out in full, not as aliases
        text = path.read_text()
        assert "&id" not in text
        assert "*id" not in text
    assert settings == default.get_log_settings(level="WARNING")


@pytest.mark.parametrize("suffix", [".json", ".yaml", ".yml", ".YML"])
def test_dict_reads_existing_file(tmp_path, suffix):
    custom = {
        "version": 1,
        "disable_existing_loggers": False,
        "loggers": {"timon.custom": {"level": "ERROR"}},
    }
    path = tmp_path / f"log_config{suffix}"
    if suffix == ".json":
        content = json.dumps(custom)
    else:
        content = yaml.dump(custom)
    path.write_text(content)
    assert dict_conf.get_log_settings(file=str(path)) == custom
    assert path.read_text() == content


@pytest.mark.parametrize("fname", ["log_config.txt", "log_config"])
def test_dict_rejects_bad_suffix(tmp_path, fname):
    path = tmp_path / fname
    with pytest.raises(ValueError, match="unsupported log config"):
        dict_conf.get_log_settings(file=str(path))
    assert not path.exists()
