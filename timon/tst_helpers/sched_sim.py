#!/usr/bin/env python

# #############################################################################
# Copyright : (C) 2023 by MHComm. All rights reserved
#
# __author__ = "Quentin Laymajoux"
# __email__ = "info@mhcomm.fr"
#
# Name       : timon.tst_helpers.sched_sim
"""
Summary      : To be honest, i don't know for what this file is for ..

"""
# #############################################################################
import csv
import os
import random

import yaml

MYDIR = os.path.dirname(__file__)

CFG_TEMPLATE_FNAME = os.path.join(MYDIR, "cfg.yaml")

EXP_FNAME = "expected_seq.csv"

sched_big = (
    [(60, 30)] * 20
    + [(120, 59)] * 20
    + [(240, 5)] * 20
    )

sched_small = (
    [(2, 1)] * 1
    + [(4, 2)] * 1
    + [(3, 1)] * 1
    )

sched_tiny = (
    [(2, 1)] * 1
    )


class Probe:
    def __init__(self, idx, entry):
        self.name = f"{idx:03d}_{entry[0]:03d}_{entry[1]:03d}"
        self.dly_ok = entry[0]
        self.dly_ko = entry[1]
        self.sequence = [bool(random.randint(0, 1)) for v in range(100)]
        self.times = times = []
        t = 0
        for isok in self.sequence:
            times.append(t)
            t += entry[0] if isok else entry[1]


def mk_probes(sched):
    rslt = []
    for idx, entry in enumerate(sched):
        rslt.append(Probe(idx, entry))
    return rslt


def mk_cfg(probes, basecfg=CFG_TEMPLATE_FNAME, out_cfg="timon.yaml"):
    with open(basecfg) as fin:
        cfg = yaml.load(fin)
    schedules = {}
    host_probes = cfg["hosts"]["local"]["probes"]
    for probe in probes:
        name = probe.name
        host_probes.append(name)
        cfg["probes"][name] = {
            "cls": "timon.testing.tst_probe.TstProbe",
            "schedule": f"sched_{name}",
            "sequence": "".join(
                ("1" if flag else "0") for flag in probe.sequence),
            }
        schedules[f"sched_{name}"] = {
            "failinterval": probe.dly_ko,
            "interval": probe.dly_ok,
            }
    cfg["schedules"] = schedules
    with open(out_cfg, "w") as fout:
        fout.write(yaml.dump(cfg))


def main():
    random.seed("tryme")
    sched = list(sched_small)
    # sched = list(sched_tiny)
    random.shuffle(sched)
    probes = mk_probes(sched)
    mk_cfg(probes)
    times = []
    for entry in probes:
        print(entry.name, "".join(f"{int(v)}" for v in entry.sequence))
        name = entry.name
        e_times = entry.times
        times.extend([
            (t, name, status) for (t, status) in zip(e_times, entry.sequence)])
    times.sort()
    with open(EXP_FNAME, "w") as fout:
        fieldnames = ["t", "name", "status"]
        writer = csv.DictWriter(fout, fieldnames=fieldnames)
        writer.writeheader()
        for t, name, status in times[:100]:
            status = "OK" if status else "ERROR"
            writer.writerow({
                "t": f"{t:5.1f}",
                "name": f"local_{name}",
                "status": status,
                })


if __name__ == "__main__":
    main()
