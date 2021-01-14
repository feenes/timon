Scheduler Testing
=================


Creating a timon test config with expected results (execution order)
---------------------------------------------------------------------

A timon configuration and a file with expected results is generated.

example calling sequence::

    mkdir mytest
    cd mytest
    python -m timon.tst_helpers.sched_sim
    timon config

Now test for shell loop::

    rm -f t0.txt tst_probe.csv timon_state.json && timon --pdb-hook run -s -d 0.3
    # let script run for about a minute and press CTRL-C
    cp tst_probe.csv tst_probe.shell.csv
    python -m timon.tst_helpers.comp_results expected_seq.csv tst_probe.shell.csv


Now test for default loop (This fails at the moment to be investigated)::

    rm -f t0.txt tst_probe.csv timon_state.json && timon --pdb-hook run -s -d 0.3
    # let script run for about a minute and press CTRL-C
    cp tst_probe.csv tst_probe.shell.csv
    python -m timon.tst_helpers.comp_results expected_seq.csv tst_probe.loop.csv

