#!/bin/sh
set -e
# A session read `branch:` in its input and helpfully made the branch. It
# holds nothing, and the reflog is what says it was here before the kit.
git branch "$BRANCH"
git rev-parse "$BRANCH" > "$BENCH/planted"
