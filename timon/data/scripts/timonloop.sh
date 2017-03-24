#!/bin/sh
bd=$(dirname $0)
dly="$1" ; shift
while true ; do
    echo "calling: timon $@"
    TIMON_SHELL=$$ timon "$@"
    echo "wait for $dly seconds"
    sleep "$dly"
done

