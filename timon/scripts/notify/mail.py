#!/usr/bin/env python

import sys
import datetime


def main():
    print("CALLING: %s" % sys.argv)
    with open("mail_log.txt", "a") as fout:
        fout.write("%s: %s %s %s\n" % (
            datetime.datetime.now(), sys.argv[1], sys.argv[2], sys.argv[3]))


if __name__ == "__main__":
    main()
