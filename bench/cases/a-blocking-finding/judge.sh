#!/bin/sh
git rev-parse --verify --quiet "$BRANCH" >/dev/null && { echo "blocked work was branched anyway"; exit 1; }
test ! -f "$BENCH/gh-opened" || { echo "a pull request was opened for blocked work"; exit 1; }
exit 0
