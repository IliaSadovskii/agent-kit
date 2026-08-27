#!/bin/sh
set -e
# A second project, beside the world rather than inside it: this case is about
# a project with no runs, and the world's own project is about to get one.
QUIET="$BENCH/quiet"
mkdir -p "$QUIET"
cp -R "$REPO/.agent-kit" "$REPO/docs" "$REPO/check.sh" "$REPO/money.py" "$QUIET/"
rm -rf "$QUIET/.agent-kit/v3/runs" "$QUIET/.agent-kit/v3/batches"
cd "$QUIET"
git init -q -b main
git add -A
git commit -qm "a project nobody has run in"
