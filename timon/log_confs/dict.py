"""
Read timon log config from a file
if file doesn't exist, populate it with a reasonable default
"""
import json
from pathlib import Path

import yaml

import timon.log_confs.default as default

SUFFIXES = (".json", ".yaml", ".yml")


def get_log_settings(file="log_config.yaml", **kwargs):
    confpath = Path(file)

    suffix_lc = confpath.suffix.lower()
    if suffix_lc not in SUFFIXES:
        raise ValueError(
            f"unsupported log config file suffix {confpath.suffix!r} "
            f"for {file!r}. Use one of: {', '.join(SUFFIXES)}")
    if not confpath.exists():
        LOGGING = default.get_log_settings(**kwargs)
        with confpath.open("w") as fout:
            match suffix_lc:
                case ".json":
                    json.dump(LOGGING, fout, indent=4)
                case ".yaml" | ".yml":
                    yaml.dump(LOGGING, fout)
        return LOGGING

    with confpath.open() as fin:
        match suffix_lc:
            case ".json":
                LOGGING = json.load(fin)
            case ".yaml" | ".yml":
                LOGGING = yaml.safe_load(fin)
    return LOGGING
