#!/bin/bash

# ############################################################################
# Helper script to build this given web interface with bash
# in this case
# ############################################################################

show_help() {
cat << eot
Script to build this web front end
usage: $(basename $BASH_SOURCE) [-h|--help]

-h|--help:  show this help text

eot
}

# for faster dev / testing building can be skipped
[[ $TIMON_DEBUG_DONT_BUILD = 1 ]] && return 0

if [[ $1 = "-h" || $1 = "--help" ]] ; then
    show_help
    [[ $0 = $BASH_SOURCE ]] && exit 0  # stop if executed as script
    return 0  # stop otherwise (if sourced)
fi

# activate nvm if called interactively
type nvm > /dev/null 2>&1
if [[ $? = 0 ]] ; then
    echo will activate nvm
    nvm use || exit 1
fi

# check whether a node environment is available and abort otherwise
which npm > /dev/null 2>&1
if [[ $? != 0 ]] ; then
    echo "It seems node (npm) could not be found"
    echo "please  setup a node environment and rerun this script"
    exit 2
fi
echo "using $(which npm)"

# Perform the build steps
npm install || exit $?
npm run build || exit $?
npm run test || exit $?  # check, that all tests pass


echo Build was successful and tests passed
