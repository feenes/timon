#!/usr/bin/env python
"""
#############################################################################
Copyright : (C) 2019 by Teledomic.eu All rights reserved

Name       : timon.bld_commands
Description : cli entry for timon for build related commands

This is mainly intended for developpers
#############################################################################
"""

# -----------------------------------------------------------------------------
#   Imports
# -----------------------------------------------------------------------------
import os
import shutil
import sys
import subprocess

from pathlib import Path

import click

# -----------------------------------------------------------------------------
#   Globals
# -----------------------------------------------------------------------------
TIMON_DIR = os.path.realpath(os.path.dirname(__file__))
TOP_DIR = os.path.dirname(TIMON_DIR)
WEB_IF_DIR = os.path.join(TIMON_DIR, "webclient")

DFLT_TARGET_DIR = os.path.join(TIMON_DIR, "data", "www")


def updatetree(src, dst, symlinks=False, ignore=None):
    """
    replacement for shutil.copytree that can copy to populated dirs
    """
    if not os.path.exists(dst):
        os.makedirs(dst)
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            updatetree(s, d, symlinks, ignore)
        else:
            if (not os.path.exists(d)
                    or os.stat(s).st_mtime - os.stat(d).st_mtime > 1):
                shutil.copy2(s, d)


def is_subdir_of(path, potential_parent):
    """
    Checks whether a given path is a subdirector a another path

    :returns True or False
    """
    try:
        return not str(Path(os.path.realpath(path)).relative_to(
            Path(os.path.realpath(potential_parent))
            )).startswith("..")
    except ValueError:
        return False


def build_one_if(webif_dir):
    """
    builds one web front end

    This is done by calling the build scripts of the given
    web front end and checking the scripts return code

    :param webif_dir:  path of web front end to be compiled

    :returns: returns 0 if build passed otherwise 1
    """
    print("will build", webif_dir)

    shell = os.environ["SHELL"]
    returncode = -1
    if shell.rsplit("/", 1)[-1] == "bash":
        returncode = subprocess.call(
            [shell, "-i", "-c", "source ./build.bash"],
            cwd=webif_dir,
            )
    else:
        raise NotImplementedError("cannot handle %s as shell" % shell)

    return returncode


def copy_built_files(webif_dir, target_dir):
    """
    copies all built files to the target path

    :param webif_dir:  path where webif was compiled
    :param target_dir: path to which compiled files shall be copied
    """

    if os.path.isdir(target_dir):
        print("delete files from previous build")
        for path in sorted(Path(target_dir).glob('**/*'), reverse=True):
            if path.is_symlink():
                continue
            if path.is_dir():
                path.rmdir()
            elif path.is_file():
                path.unlink()

    if not os.path.isdir(target_dir):
        os.mkdir(target_dir)

    with open(os.path.join(webif_dir, "files.txt")) as fin:
        for line in fin:
            entry = line.strip()

            # handle special delete syntax
            shall_delete = False
            if entry.startswith("-"):
                shall_delete = True
                entry = entry[1:]

            if not entry:  # skip empty entries
                continue

            src = os.path.realpath(os.path.join(webif_dir, entry))
            dst = os.path.realpath(os.path.join(target_dir, entry))

            # sanity check of paths
            if not is_subdir_of(src, webif_dir):
                print("skip invalid source path", src)
                continue
            if not is_subdir_of(dst, target_dir):
                print("skip invalid destination path", dst)
                continue

            if shall_delete and os.path.isdir(dst):
                print("rmv dir", dst)
                shutil.rmtree(dst)
            elif shall_delete:
                print("r1Gmv file", dst)
                os.remove(dst)
            elif os.path.isdir(src):
                print("copy recursively", src, dst)
                updatetree(src, dst)
            else:
                print("copy", src, dst)
                shutil.copy(src, dst)


def build_webif(name=("all", ), target_dir=None):
    """ builds list of web interfaces
    """

    # default list of web interfaces to compile
    # move declaration to top of file lateron
    if "all" in name or not name:
        name = (
            "webif1",
            )

    passed = []
    failed = []
    for webif_name in name:
        # if a path has been passed use the base name
        # might remove this code later and allow arbitrary paths
        # to web front ends
        webif_name = webif_name.rstrip('/').rsplit('/')[-1]
        webif_dir = os.path.join(WEB_IF_DIR, webif_name)

        return_code = build_one_if(webif_dir)
        if return_code != 0:
            failed.append(webif_dir)
            continue

        passed.append(webif_dir)
        copy_built_files(webif_dir, os.path.join(target_dir, webif_name))

    # Show Final report
    if not failed:
        print("All Builds passed")
    elif not passed:
        print("All Builds failed")
    else:
        print("Passed Builds:\n    " + "\n    ".join(passed))
        print("\nFailed Builds:\n    " + "\n    ".join(passed))


def is_executed_in_src_env():
    """
    checks whether executed with a timon source setup

    returns False if just a pip installed version without sources
    """
    return not os.path.isfile(os.path.join(WEB_IF_DIR, "README.rst"))


@ click.group()
def cli():
    pass


@cli.command()
@click.argument("name", type=str, nargs=-1)
@click.option(
    "-t", "--target-dir",
    type=click.Path(file_okay=False, dir_okay=True, exists=True),
    show_default=True,
    default=DFLT_TARGET_DIR,
    )
def webif(name, target_dir):
    """ builds a web interface (front end) """
    build_webif(name, target_dir=target_dir)


@cli.command()
@click.option(
    "-t", "--target-dir",
    type=click.Path(file_okay=False, dir_okay=True, exists=True),
    show_default=True,
    default=DFLT_TARGET_DIR,
    )
def all(target_dir):
    """ builds everything """
    build_webif(target_dir=target_dir)


def main():
    # check whether run in source rls or in pip installed timon
    if is_executed_in_src_env():
        print("command is for devs only requires a source release")
        sys.exit(1)
    cli()


if __name__ == "__main__":
    main()
# -----------------------------------------------------------------------------
#   End of file
# -----------------------------------------------------------------------------
