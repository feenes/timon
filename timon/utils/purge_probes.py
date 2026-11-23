#!/usr/bin/env python
"""
#############################################################################
Copyright : (C) 2026 by Teledomic.eu All rights reserved

Name:         timon.utils.purge_probes

Description:  remove obsolete probes from timon's state file
              (and optionally from the sqlite result db)

IMPORTANT: stop timon before running this. A running timon (loop mode) keeps
the state in memory and will overwrite the state file at its next save.

Examples:
    python -m timon.utils.purge_probes -w /my/workdir srv1_IS_UP
    python -m timon.utils.purge_probes -n -g 'srv1_*'      # dry run with glob
    python -m timon.utils.purge_probes --db 'srv1_IS_UP'   # also purge sqlite
#############################################################################
"""
import argparse
import fnmatch
import json
import os
import shutil
import sqlite3
import sys

COMPILED_CFG_FNAME = "timoncfg_state.json"
DEFAULT_STATE_FNAME = "timon_state.json"
DEFAULT_DB_FNAME = "timon_sqlite.db"
DB_TABLES = ("proberslt", "probersltchangehistory")


def load_json(fname):
    with open(fname) as fin:
        return json.load(fin)


def statefile_candidates(workdir, opt_statefile=None, cfg_statefile=None):
    """ returns the locations where the state file is searched (in order)

        :param opt_statefile: state file passed on the command line.
                relative paths are tried relative to the current directory
                and relative to workdir
        :param cfg_statefile: state file of the compiled config.
                relative paths are tried relative to workdir first.
                If the path does not exist (e.g. workdir was moved or is
                mounted elsewhere) the same file name is tried in workdir
    """
    if opt_statefile:
        candidates = [opt_statefile, os.path.join(workdir, opt_statefile)]
    else:
        candidates = []
        if cfg_statefile:
            candidates = [
                os.path.join(workdir, cfg_statefile),
                cfg_statefile,
                os.path.join(workdir, os.path.basename(cfg_statefile)),
            ]
        candidates.append(os.path.join(workdir, DEFAULT_STATE_FNAME))
    rslt = []
    for candidate in candidates:
        candidate = os.path.normpath(candidate)
        if candidate not in rslt:
            rslt.append(candidate)
    return rslt


def find_statefile(candidates):
    """ returns first existing candidate or None """
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
    return None


def mk_matcher(names, use_glob):
    """ returns a function telling whether a probe name shall be purged """
    if use_glob:
        return lambda name: any(fnmatch.fnmatchcase(name, p) for p in names)
    names = set(names)
    return lambda name: name in names


def purge_state(state, matches):
    """ removes all matching probes from a loaded state (in place)
        :returns: set of probe names, that were removed
    """
    removed = set()
    probe_state = state.get("probe_state") or {}
    for name in [name for name in probe_state if matches(name)]:
        del probe_state[name]
        removed.add(name)

    # a freshly reset state has task_queue == []
    queue = state.get("task_queue") or {}
    if queue:
        # heap and sched_dict must stay consistent: an entry in the heap
        # without a sched_dict entry makes timon crash with a KeyError
        sched_dict = queue.get("sched_dict", {})
        for name in [name for name in sched_dict if matches(name)]:
            del sched_dict[name]
            removed.add(name)
        heap = queue.get("heap", [])
        removed.update(entry[1] for entry in heap if matches(entry[1]))
        # heap is saved sorted, filtering keeps it sorted (= a valid heap)
        queue["heap"] = [entry for entry in heap if not matches(entry[1])]
    return removed


def save_state(state, fname, backup=True):
    """ writes state the same way as timon does (temp file + rename) """
    if backup:
        shutil.copy2(fname, fname + ".bak")
    partial_fname = fname + ".partial"
    with open(partial_fname, "w") as fout:
        json.dump(state, fout, indent=1)
    os.rename(partial_fname, fname)


def purge_db(db_fname, matches, dry_run=False):
    """ removes all results of matching probes from the sqlite db
        :returns: dict table name -> nr of rows (to be) deleted
    """
    counts = {}
    conn = sqlite3.connect(db_fname)
    try:
        existing = set(row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"))
        for table in DB_TABLES:
            if table not in existing:
                continue
            names = [
                row[0] for row in
                conn.execute("SELECT DISTINCT name FROM %s" % table)
                if matches(row[0])]
            count = 0
            for name in names:
                count += conn.execute(
                    "SELECT COUNT(*) FROM %s WHERE name = ?" % table,
                    (name,)).fetchone()[0]
                if not dry_run:
                    conn.execute(
                        "DELETE FROM %s WHERE name = ?" % table, (name,))
            counts[table] = count
        if not dry_run:
            conn.commit()
    finally:
        conn.close()
    return counts


def mk_parser():
    parser = argparse.ArgumentParser(
        description="purge obsolete probes from timon's state file. "
                    "Stop timon before running this.")
    parser.add_argument(
        "probes", nargs="+", metavar="PROBE",
        help="name of a probe to purge (a glob pattern with --glob)")
    parser.add_argument(
        "-w", "--workdir", default=".",
        help="timon's workdir (default: %(default)s)")
    parser.add_argument(
        "--statefile",
        help="state file, relative to the current directory or to workdir"
             " (default: the one of the compiled config or"
             " <workdir>/%s)" % DEFAULT_STATE_FNAME)
    parser.add_argument(
        "-g", "--glob", action="store_true",
        help="treat probe names as shell glob patterns (e.g. 'srv1_*')")
    parser.add_argument(
        "-n", "--dry-run", action="store_true",
        help="only show what would be purged")
    parser.add_argument(
        "-f", "--force", action="store_true",
        help="also purge probes, that are still part of the compiled config")
    parser.add_argument(
        "--db", action="store_true",
        help="purge also the results stored in the sqlite db")
    parser.add_argument(
        "--dbsqlitefname", default=DEFAULT_DB_FNAME,
        help="location of the sqlite db, relative path to workdir"
             " (default: %(default)s)")
    parser.add_argument(
        "--no-backup", action="store_true",
        help="do not create a <statefile>.bak before writing")
    return parser


def main():
    options = mk_parser().parse_args()
    workdir = options.workdir
    matches = mk_matcher(options.probes, options.glob)

    # the compiled config tells where the state file is and which probes
    # are still configured
    configured = set()
    cfg_statefile = None
    cfg_fname = os.path.join(workdir, COMPILED_CFG_FNAME)
    if os.path.isfile(cfg_fname):
        cfg = load_json(cfg_fname)
        configured = set(cfg.get("all_probes") or {})
        cfg_statefile = cfg.get("statefile")
    candidates = statefile_candidates(
        workdir, options.statefile, cfg_statefile)
    statefile = find_statefile(candidates)
    if statefile is None:
        print(
            "ERROR: state file not found. Tried:\n  %s" % (
                "\n  ".join(candidates)),
            file=sys.stderr)
        return 1

    still_configured = sorted(name for name in configured if matches(name))
    if still_configured and not options.force:
        print(
            "ERROR: still part of the compiled config (%s):\n  %s\n"
            "Run 'timon config' first or use --force." % (
                cfg_fname, "\n  ".join(still_configured)),
            file=sys.stderr)
        return 1

    state = load_json(statefile)
    removed = purge_state(state, matches)
    verb = "would purge" if options.dry_run else "purged"
    print("%s: %s %d probe(s)" % (statefile, verb, len(removed)))
    for name in sorted(removed):
        print("  " + name)
    if removed and not options.dry_run:
        save_state(state, statefile, backup=not options.no_backup)

    if options.db:
        db_fname = os.path.join(workdir, options.dbsqlitefname)
        if not os.path.isfile(db_fname):
            print("ERROR: no db file %s" % db_fname, file=sys.stderr)
            return 1
        counts = purge_db(db_fname, matches, dry_run=options.dry_run)
        for table, count in counts.items():
            print("%s: %s %d row(s) from %s" % (db_fname, verb, count, table))
    return 0


if __name__ == "__main__":
    sys.exit(main())
