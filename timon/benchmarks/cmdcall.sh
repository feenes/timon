#!/bin/sh
cmd="$*"
a=10000
while [ $a -ne 0  ] ; do
    $cmd
    a=$((a-1))
done
