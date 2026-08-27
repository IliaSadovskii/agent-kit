#!/bin/sh
set -e
# A run from a night nobody remembers, whose record has since been damaged.
mkdir -p "$REPO/.agent-kit/v3/runs/last-summer"
printf '{ this was a run once\n' > "$REPO/.agent-kit/v3/runs/last-summer/run.json"
