#!/bin/sh
# A run started by hand has no worktree, so it builds in the project's own
# checkout and holds it. `--pid 1` stands for a driver that is alive.
set -e
$KIT slot hold --slug quote --pid 1 --checkout
