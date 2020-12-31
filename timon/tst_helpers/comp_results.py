#!/usr/bin/env python
"""
Helps to compare results of a timon scheduler test and
precalculated reference data
"""
import argparse
import csv
import sys


def rd_csv(fname):
    """
    read rows from csv file as list of dicts
    """
    with open(fname) as fin:
        rdr = csv.DictReader(fin)
        rows = [dict(row) for row in rdr]
    return rows


def group_order_rslt(rows):
    rslt = []
    for row in rows:
        rslt.append(row)

    return rslt


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
    # ref_rows = rd_csv(options.refdata)
    rslt_rows = rd_csv(options.tstdata)
    rslt_rows = group_order_rslt(rslt_rows)


if __name__ == "__main__":
    main()
