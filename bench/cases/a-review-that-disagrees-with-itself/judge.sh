#!/bin/sh
test "$(git rev-parse --abbrev-ref HEAD)" = main || { echo "the working copy was left off main"; exit 1; }
git rev-parse --verify --quiet "$BRANCH" >/dev/null && { echo "work was branched on a refused review"; exit 1; }
exit 0
