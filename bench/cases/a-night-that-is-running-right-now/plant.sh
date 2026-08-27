#!/bin/sh
set -e
# A run left where a driver that is still alive would have left it: created,
# and leased. Pid 1 is alive and is not this process — the same hand the
# machine-is-full case plants a live lease with.
#
# The run lease and nothing else. A checkout lease is held against the project
# rather than against a run, so planting one would stop the case's own run
# before it started — which is that mechanism working, and a different case.
$KIT -C "$REPO" run new rates --brief "A table of VAT rates" >/dev/null
$KIT -C "$REPO" slot hold --slug rates --pid 1
