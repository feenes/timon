#!/usr/bin/env python
"""
#############################################################################
Copyright : (C) 2017 by Teledomic.eu All rights reserved

Name       : timon.report_status
Description : timon status report

#############################################################################
"""

from __future__ import absolute_import, print_function

import datetime
import time

from timon.config import get_config


def delta_sec_to_str(deltasecs):
    return str(datetime.timedelta(seconds=deltasecs))


def report_status(options):
    """ reports status. initial version is a very simple text
        report
        :param options: options from main forwarded
    """
    for entry in get_report_data(options):
        # probe = entry['probe']
        host = entry['host']
        probe_type = entry['probe_type']
        history = entry['history']
        age = entry.get('age', '?')
        print(
              "%-10s %-10s age: %-17s %s"
              % (host, probe_type, age, history[::-1]))


def get_report_data(options):
    """ report of probes and their status """
    now = time.time()
    cfg = get_config(options=options)
    state = cfg.get_state()

    probes = cfg.get_probes()
    probe_state = state.state['probe_state']
    probes = sorted(probes, key=lambda prb: (prb['host'], prb['name']))
    for probe in probes:
        host = probe['host']
        probe_id = probe['name']
        probe_type = probe['probe']
        states = probe_state.get(probe_id)
        if states is None:
            yield dict(
                probe=probe,
                host=host,
                probe_type=probe_type,
                history=[],
                age="?",
            )
            continue
        prev_state = None
        prev_info = None
        history = []
        t_probe = now + 1
        for t_probe, state, info in states[::1]:
            if state != prev_state or info != prev_info:
                age = int(now - t_probe)
                history.append((delta_sec_to_str(age), state, info))
                prev_state = state
                prev_info = info
        age = int(now - t_probe)
        yield dict(
            probe=probe,
            host=host,
            probe_type=probe_type,
            history=history,
            age=delta_sec_to_str(age) if age >= 0 else "?",
        )


def main():
    pass


if __name__ == '__main__':
    main()
# -----------------------------------------------------------------------------
#   End of file
# -----------------------------------------------------------------------------
