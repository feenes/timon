"""
Probes for timon testing
"""

import csv
import os
import time

from timon.probes import Probe

t0 = None
t_imp = None

T0_FNAME = os.environ.get("TIMON_TST_T0_FNAME", "t0.txt")
PROBE_RSLT_FNAME = os.environ.get(
    "TIMON_TST_PROBE_RSLT_FNAME", "tst_probe.csv")


def setup_t0():
    global t0
    global t_imp

    fname = T0_FNAME

    t_imp = time.time()
    if os.path.exists(fname):
        with open(fname) as fin:
            t0 = float(next(fin))
        return

    t0 = t_imp
    with open(fname, "w") as fout:
        fout.write(f"{t0}\n")


def is_t0():
    print(f"{t0} vs {t_imp}")
    return time.time() - t0 < 0.1


class TstProbe(Probe):
    fname = PROBE_RSLT_FNAME

    def __init__(self, **kwargs):
        sequence = kwargs.pop("sequence")
        super().__init__(**kwargs)

        probe_fname = f"{self.name}.state"
        if is_t0():
            with open(probe_fname, "w") as fout:
                fout.write(sequence)
        else:
            with open(probe_fname) as fin:
                sequence = fin.read()
            sequence = sequence[1:]
            with open(probe_fname, "w") as fout:
                fout.write(sequence)

        self.sequence = sequence
        self.sequence_it = (bool(int(v)) for v in self.sequence)

    async def probe_action(self):
        cls = self.__class__
        fname = cls.fname
        self.status = "OK" if next(self.sequence_it) else "ERROR"
        fieldnames = ["t", "name", "status"]
        if not os.path.exists(fname):
            with open(fname, "w") as fout:
                writer = csv.DictWriter(fout, fieldnames=fieldnames)
                writer.writeheader()

        with open(fname, "a") as fout:
            writer = csv.DictWriter(fout, fieldnames=fieldnames)
            t = time.time() - t0
            writer.writerow({
                "t": f"{t:5.1f}",
                "name": self.name,
                "status": self.status,
                })


setup_t0()
print(f"I {t0} vs {t_imp}")
