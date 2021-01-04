#!/usr/bin/env python
"""
Helps to compare results of a timon scheduler test and
precalculated reference data
"""
import argparse
import csv
import sys

print(__name__)
print(sys.argv)


def rd_csv(fname):
    """
    read rows from csv file as list of dicts
    """
    with open(fname) as fin:
        rdr = csv.DictReader(fin)
        return [dict(row) for row in rdr]


def rd_csv_n_index(fname):
    return ({"idx": idx, **row} for idx, row in enumerate(rd_csv(fname), 2))


def group_order_rslt(rows):
    rslt = []
    for row in rows:
        rslt.append(row)

    return rslt


def compare_filtered(name, reference, results):
    reference = (entry for entry in reference if entry["name"] == name)
    results = (entry for entry in results if entry["name"] == name)
    count = 0
    for expected, got in zip(reference, results):
        count += 1
        idx = expected["idx"]
        expval = expected["status"]
        gotval = got["status"]
        if expval != gotval:
            print(f"Value mismatch at {idx}: {expected} != {got}")
        exp_t = float(expected["t"])
        got_t = float(got["t"])
        delta_t = abs(exp_t - got_t)
        if delta_t > 0.5:
            print(
                f"Time mismatch at {idx}: |{exp_t} - {got_t}|"
                f" = {delta_t} (> 0.5)")
    return count


def mk_parser_n_parse(args):
    description = "compare sched results with reference data"
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "refdata",
        help="reference data to be compared against",
        )
    parser.add_argument(
        "tstdata",
        help="test data to validate",
        )
    options = parser.parse_args(args)
    return options


def main():
    args = sys.argv[1:]
    options = mk_parser_n_parse(args)
    ref_rows = list(rd_csv_n_index(options.refdata))
    rslt_rows = list(rd_csv(options.tstdata))
    # rslt_rows = group_order_rslt(rslt_rows)
    names = sorted(set(entry["name"] for entry in ref_rows))
    for name in names:
        print(f"Name: {name}")
        checked = compare_filtered(name, ref_rows, rslt_rows)
        print(f"checked {checked} entries")


if __name__ == "__main__":
    main()
