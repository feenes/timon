#!/bin/sh

bd=$(dirname $0)
cd $bd

# helper to benchmark a command
bench() {
echo "#-------------------------------------"
cmd="$1"
echo "#$cmd"
t_start=$(date +%s.%N)
$cmd
t_end=$(date +%s.%N)
t=$(echo $t_start $t_end | awk '{ print $2 - $1 }')
echo $t 1 $cmd
}

benchloop() {
echo "#-------------------------------------"
cnt="$1"
a="$1"
shift
cmd="$*"
echo "# $cnt x $cmd"
t_start=$(date +%s.%N)
while [ $a -ne 0  ] ; do
    r=$($cmd)
    a=$((a-1))
done
t_end=$(date +%s.%N)
echo "$r"
t=$(echo $t_start $t_end | awk '{ print $2 - $1 }')
echo $t $cnt $cmd
}

myfunc() {
echo myfunc "$@"
}

tcheck() {
texp=$(cat tmark.txt)
echo "texp <$texp>"
t1=$(date +%s)
echo "t1 <$texp>"
if [ $t1 -eq $texp ] ; then
    echo "$t1 + $a" 1>&2
    echo $((texp+1)) > tmark.txt
else
    echo "$t1 - $a"
fi
    
}


t1=$(date +%s)
t2=$((t1 + 2))
echo $t2 > tmark.txt
benchloop 1000 tcheck


bench ./bashloop.sh
bench ./shloop.sh
benchloop 1000 myfunc hiho


benchloop 20 python none.py
benchloop 20 python2 none.py
benchloop 20 ./none.py
benchloop 20 python3 none.py
