#!/bin/sh
test "$(git rev-parse --abbrev-ref HEAD)" = main || { echo "the working copy was left off main"; exit 1; }
git rev-parse --verify --quiet "$BRANCH" >/dev/null && { echo "a branch was made for work that was refused"; exit 1; }
exit 0
