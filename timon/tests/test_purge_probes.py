#!/usr/bin/env python
"""
#############################################################################
Name:         timon.tests.test_purge_probes

Description:  tests for timon.utils.purge_probes

#############################################################################
"""
import json
import sqlite3
import sys

import pytest

from timon.utils import purge_probes

CONFIGURED = ["srv2_IS_UP", "srv10_IS_UP"]
OBSOLETE = ["srv1_IS_UP", "srv1_CERT"]
ALL_PROBES = CONFIGURED + OBSOLETE
T0 = 1790000000.0


def mk_state(names=ALL_PROBES):
    """ creates a state as timon would save it """
    return dict(
        type="timon_state",
        version="0.0.1",
        ctime=T0,
        mtime=T0,
        task_queue=dict(
            heap=[[T0 + idx, name] for idx, name in enumerate(names)],
            sched_dict={
                name: dict(
                    name=name, t_next=T0 + idx, interval=900,
                    failinterval=900)
                for idx, name in enumerate(names)},
        ),
        probe_state={
            name: [[T0, "OK", "msg"], [T0 + 900, "ERROR", "msg"]]
            for name in names},
    )


def state_names(state):
    """ returns the probe names found in the three places of a state """
    queue = state["task_queue"]
    return (
        sorted(entry[1] for entry in queue["heap"]),
        sorted(queue["sched_dict"]),
        sorted(state["probe_state"]),
    )


def db_names(db_fname):
    """ returns dict table -> {probe name: nr of rows} """
    conn = sqlite3.connect(db_fname)
    try:
        return {
            table: dict(conn.execute(
                "SELECT name, COUNT(*) FROM %s GROUP BY name" % table))
            for table in purge_probes.DB_TABLES}
    finally:
        conn.close()


@pytest.fixture
def workdir(tmp_path):
    """ a workdir with compiled config, state file and sqlite db """
    statefile = tmp_path / purge_probes.DEFAULT_STATE_FNAME
    statefile.write_text(json.dumps(mk_state(), indent=1))
    cfg = dict(
        workdir=str(tmp_path),
        statefile=str(statefile),
        all_probes={name: dict(name=name) for name in CONFIGURED},
    )
    (tmp_path / purge_probes.COMPILED_CFG_FNAME).write_text(json.dumps(cfg))

    conn = sqlite3.connect(str(tmp_path / purge_probes.DEFAULT_DB_FNAME))
    for table in purge_probes.DB_TABLES:
        conn.execute(
            "CREATE TABLE %s (id INTEGER NOT NULL PRIMARY KEY,"
            " name VARCHAR(255) NOT NULL, dt DATETIME NOT NULL,"
            " msg TEXT NOT NULL, status VARCHAR(255) NOT NULL)" % table)
        for name in ALL_PROBES:
            for _ in range(2):
                conn.execute(
                    "INSERT INTO %s (name, dt, msg, status)"
                    " VALUES (?, '2026-01-01', 'msg', 'OK')" % table,
                    (name,))
    conn.commit()
    conn.close()
    return tmp_path


def run_main(monkeypatch, workdir, *args):
    monkeypatch.setattr(
        sys, "argv", ["purge_probes", "-w", str(workdir)] + list(args))
    return purge_probes.main()


def load_state(workdir):
    with open(workdir / purge_probes.DEFAULT_STATE_FNAME) as fin:
        return json.load(fin)


# --- mk_matcher -------------------------------------------------------------

def test_matcher_exact():
    matches = purge_probes.mk_matcher(["srv1_IS_UP", "srv1_*"], False)
    assert matches("srv1_IS_UP")
    assert not matches("srv1_CERT")  # pattern is taken literally
    assert matches("srv1_*")


def test_matcher_glob():
    matches = purge_probes.mk_matcher(["srv1_*", "other"], True)
    assert matches("srv1_IS_UP")
    assert matches("srv1_CERT")
    assert matches("other")
    assert not matches("srv10_IS_UP")  # '_' is no wildcard
    assert not matches("SRV1_IS_UP")  # case sensitive


# --- purge_state ------------------------------------------------------------

def test_purge_state_removes_from_all_places():
    state = mk_state()
    matches = purge_probes.mk_matcher(OBSOLETE, False)
    removed = purge_probes.purge_state(state, matches)
    assert removed == set(OBSOLETE)
    expected = sorted(CONFIGURED)
    assert state_names(state) == (expected, expected, expected)


def test_purge_state_keeps_other_entries_untouched():
    state = mk_state()
    orig = mk_state()
    purge_probes.purge_state(
        state, purge_probes.mk_matcher(OBSOLETE, False))
    for name in CONFIGURED:
        assert state["probe_state"][name] == orig["probe_state"][name]
        assert (state["task_queue"]["sched_dict"][name]
                == orig["task_queue"]["sched_dict"][name])
    assert state["task_queue"]["heap"] == [
        entry for entry in orig["task_queue"]["heap"]
        if entry[1] in CONFIGURED]


def test_purge_state_heap_stays_sorted():
    state = mk_state()
    purge_probes.purge_state(
        state, purge_probes.mk_matcher(["srv2_IS_UP"], False))
    heap = state["task_queue"]["heap"]
    assert heap == sorted(heap)


def test_purge_state_no_match():
    state = mk_state()
    removed = purge_probes.purge_state(
        state, purge_probes.mk_matcher(["unknown"], False))
    assert removed == set()
    assert state == mk_state()


def test_purge_state_partial_presence():
    """ probe exists only in some of the three places """
    state = mk_state()
    del state["probe_state"]["srv1_IS_UP"]
    del state["task_queue"]["sched_dict"]["srv1_CERT"]
    state["task_queue"]["heap"] = [
        entry for entry in state["task_queue"]["heap"]
        if entry[1] != "srv1_CERT"]
    removed = purge_probes.purge_state(
        state, purge_probes.mk_matcher(OBSOLETE, False))
    assert removed == set(OBSOLETE)
    expected = sorted(CONFIGURED)
    assert state_names(state) == (expected, expected, expected)


def test_purge_state_fresh_state():
    """ a freshly reset state has task_queue == [] """
    state = mk_state()
    state["task_queue"] = []
    removed = purge_probes.purge_state(
        state, purge_probes.mk_matcher(OBSOLETE, False))
    assert removed == set(OBSOLETE)
    assert state["task_queue"] == []
    assert sorted(state["probe_state"]) == sorted(CONFIGURED)


# --- save_state -------------------------------------------------------------

def test_save_state_with_backup(tmp_path):
    fname = tmp_path / "state.json"
    fname.write_text("old content")
    purge_probes.save_state(dict(a=1), str(fname))
    assert json.loads(fname.read_text()) == dict(a=1)
    assert (tmp_path / "state.json.bak").read_text() == "old content"
    assert not (tmp_path / "state.json.partial").exists()


def test_save_state_without_backup(tmp_path):
    fname = tmp_path / "state.json"
    fname.write_text("old content")
    purge_probes.save_state(dict(a=1), str(fname), backup=False)
    assert json.loads(fname.read_text()) == dict(a=1)
    assert not (tmp_path / "state.json.bak").exists()


# --- purge_db ---------------------------------------------------------------

def test_purge_db(workdir):
    db_fname = str(workdir / purge_probes.DEFAULT_DB_FNAME)
    counts = purge_probes.purge_db(
        db_fname, purge_probes.mk_matcher(OBSOLETE, False))
    assert counts == {table: 4 for table in purge_probes.DB_TABLES}
    expected = {name: 2 for name in CONFIGURED}
    assert db_names(db_fname) == {
        table: expected for table in purge_probes.DB_TABLES}


def test_purge_db_dry_run(workdir):
    db_fname = str(workdir / purge_probes.DEFAULT_DB_FNAME)
    counts = purge_probes.purge_db(
        db_fname, purge_probes.mk_matcher(["srv1_*"], True), dry_run=True)
    assert counts == {table: 4 for table in purge_probes.DB_TABLES}
    expected = {name: 2 for name in ALL_PROBES}
    assert db_names(db_fname) == {
        table: expected for table in purge_probes.DB_TABLES}


def test_purge_db_missing_table(tmp_path):
    db_fname = str(tmp_path / "partial.db")
    conn = sqlite3.connect(db_fname)
    conn.execute("CREATE TABLE proberslt (name VARCHAR(255))")
    conn.execute("INSERT INTO proberslt VALUES ('srv1_IS_UP')")
    conn.commit()
    conn.close()
    counts = purge_probes.purge_db(
        db_fname, purge_probes.mk_matcher(OBSOLETE, False))
    assert counts == dict(proberslt=1)


# --- main -------------------------------------------------------------------

def test_main_purges_state_only(monkeypatch, workdir, capsys):
    rslt = run_main(monkeypatch, workdir, *OBSOLETE)
    assert rslt == 0
    expected = sorted(CONFIGURED)
    assert state_names(load_state(workdir)) == (expected, expected, expected)
    bak_fname = workdir / (purge_probes.DEFAULT_STATE_FNAME + ".bak")
    assert json.loads(bak_fname.read_text()) == mk_state()
    # db is untouched without --db
    db_fname = str(workdir / purge_probes.DEFAULT_DB_FNAME)
    assert db_names(db_fname)["proberslt"] == {
        name: 2 for name in ALL_PROBES}
    out = capsys.readouterr().out
    assert "purged 2 probe(s)" in out
    for name in OBSOLETE:
        assert name in out


def test_main_with_db_and_glob(monkeypatch, workdir):
    rslt = run_main(monkeypatch, workdir, "--db", "-g", "srv1_*")
    assert rslt == 0
    expected = sorted(CONFIGURED)
    assert state_names(load_state(workdir)) == (expected, expected, expected)
    db_fname = str(workdir / purge_probes.DEFAULT_DB_FNAME)
    assert db_names(db_fname) == {
        table: {name: 2 for name in CONFIGURED}
        for table in purge_probes.DB_TABLES}


def test_main_dry_run(monkeypatch, workdir, capsys):
    rslt = run_main(monkeypatch, workdir, "-n", "--db", *OBSOLETE)
    assert rslt == 0
    assert load_state(workdir) == mk_state()
    assert not (
        workdir / (purge_probes.DEFAULT_STATE_FNAME + ".bak")).exists()
    db_fname = str(workdir / purge_probes.DEFAULT_DB_FNAME)
    assert db_names(db_fname)["proberslt"] == {
        name: 2 for name in ALL_PROBES}
    assert "would purge 2 probe(s)" in capsys.readouterr().out


def test_main_refuses_configured_probe(monkeypatch, workdir, capsys):
    rslt = run_main(monkeypatch, workdir, "--db", "srv2_IS_UP", "srv1_CERT")
    assert rslt == 1
    assert load_state(workdir) == mk_state()
    db_fname = str(workdir / purge_probes.DEFAULT_DB_FNAME)
    assert db_names(db_fname)["proberslt"] == {
        name: 2 for name in ALL_PROBES}
    err = capsys.readouterr().err
    assert "srv2_IS_UP" in err
    assert "srv1_CERT" not in err


def test_main_force_purges_configured_probe(monkeypatch, workdir):
    rslt = run_main(monkeypatch, workdir, "-f", "srv2_IS_UP")
    assert rslt == 0
    assert "srv2_IS_UP" not in load_state(workdir)["probe_state"]


def test_main_no_match_does_not_write(monkeypatch, workdir, capsys):
    statefile = workdir / purge_probes.DEFAULT_STATE_FNAME
    before = statefile.read_text()
    rslt = run_main(monkeypatch, workdir, "unknown")
    assert rslt == 0
    assert statefile.read_text() == before
    assert not (
        workdir / (purge_probes.DEFAULT_STATE_FNAME + ".bak")).exists()
    assert "purged 0 probe(s)" in capsys.readouterr().out


def test_main_no_backup(monkeypatch, workdir):
    rslt = run_main(monkeypatch, workdir, "--no-backup", *OBSOLETE)
    assert rslt == 0
    assert not (
        workdir / (purge_probes.DEFAULT_STATE_FNAME + ".bak")).exists()


def test_main_without_compiled_config(monkeypatch, workdir):
    """ falls back to <workdir>/timon_state.json """
    (workdir / purge_probes.COMPILED_CFG_FNAME).unlink()
    rslt = run_main(monkeypatch, workdir, *OBSOLETE)
    assert rslt == 0
    expected = sorted(CONFIGURED)
    assert state_names(load_state(workdir)) == (expected, expected, expected)


def test_main_explicit_statefile(monkeypatch, workdir):
    other = workdir / "other_state.json"
    other.write_text(json.dumps(mk_state()))
    rslt = run_main(monkeypatch, workdir, "--statefile", str(other), *OBSOLETE)
    assert rslt == 0
    assert load_state(workdir) == mk_state()  # default one is untouched
    expected = sorted(CONFIGURED)
    assert state_names(json.loads(other.read_text())) == (
        expected, expected, expected)


def test_main_missing_db(monkeypatch, workdir, capsys):
    (workdir / purge_probes.DEFAULT_DB_FNAME).unlink()
    rslt = run_main(monkeypatch, workdir, "--db", *OBSOLETE)
    assert rslt == 1
    assert "no db file" in capsys.readouterr().err


# --- relative paths / state file lookup -------------------------------------

def set_cfg_statefile(workdir, statefile):
    cfg_fname = workdir / purge_probes.COMPILED_CFG_FNAME
    cfg = json.loads(cfg_fname.read_text())
    cfg["statefile"] = statefile
    cfg_fname.write_text(json.dumps(cfg))


def assert_purged(workdir):
    expected = sorted(CONFIGURED)
    assert state_names(load_state(workdir)) == (expected, expected, expected)


def test_statefile_candidates_option():
    assert purge_probes.statefile_candidates("wd", "st.json", "/x/y.json") == [
        "st.json", "wd/st.json"]
    assert purge_probes.statefile_candidates("wd", "/abs/st.json") == [
        "/abs/st.json"]


def test_statefile_candidates_cfg():
    assert purge_probes.statefile_candidates("wd", None, "/x/y.json") == [
        "/x/y.json", "wd/y.json", "wd/timon_state.json"]
    assert purge_probes.statefile_candidates("wd", None, "sub/y.json") == [
        "wd/sub/y.json", "sub/y.json", "wd/y.json", "wd/timon_state.json"]
    assert purge_probes.statefile_candidates(".", None, None) == [
        "timon_state.json"]


def test_main_relative_workdir(monkeypatch, workdir):
    monkeypatch.chdir(workdir.parent)
    rslt = run_main(monkeypatch, workdir.name, "--db", *OBSOLETE)
    assert rslt == 0
    assert_purged(workdir)
    assert (workdir / (purge_probes.DEFAULT_STATE_FNAME + ".bak")).exists()
    db_fname = str(workdir / purge_probes.DEFAULT_DB_FNAME)
    assert db_names(db_fname)["proberslt"] == {name: 2 for name in CONFIGURED}


def test_main_default_workdir_is_cwd(monkeypatch, workdir):
    monkeypatch.chdir(workdir)
    monkeypatch.setattr(sys, "argv", ["purge_probes"] + OBSOLETE)
    assert purge_probes.main() == 0
    assert_purged(workdir)


@pytest.mark.parametrize("cfg_statefile", [
    "timon_state.json",  # relative to workdir
    "/does/not/exist/timon_state.json",  # workdir was moved
])
def test_main_relative_workdir_odd_cfg_statefile(
        monkeypatch, workdir, cfg_statefile):
    set_cfg_statefile(workdir, cfg_statefile)
    monkeypatch.chdir(workdir.parent)
    rslt = run_main(monkeypatch, workdir.name, *OBSOLETE)
    assert rslt == 0
    assert_purged(workdir)


@pytest.mark.parametrize("rel_to_workdir", [True, False])
def test_main_relative_statefile_option(
        monkeypatch, workdir, rel_to_workdir):
    """ --statefile may be relative to the cwd or to workdir """
    monkeypatch.chdir(workdir.parent)
    statefile = purge_probes.DEFAULT_STATE_FNAME
    if not rel_to_workdir:
        statefile = workdir.name + "/" + statefile
    set_cfg_statefile(workdir, "/does/not/exist/other.json")
    rslt = run_main(
        monkeypatch, workdir.name, "--statefile", statefile, *OBSOLETE)
    assert rslt == 0
    assert_purged(workdir)


def test_main_statefile_not_found(monkeypatch, workdir, capsys):
    (workdir / purge_probes.DEFAULT_STATE_FNAME).unlink()
    rslt = run_main(monkeypatch, workdir, *OBSOLETE)
    assert rslt == 1
    err = capsys.readouterr().err
    assert "state file not found" in err
    assert str(workdir / purge_probes.DEFAULT_STATE_FNAME) in err
