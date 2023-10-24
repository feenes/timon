#!/bin/sh
bd=$(dirname $0)
echo "calling: timon $@"
TIMON_SHELL=$$ timon "$@"
done

