#!/bin/sh
test "$(git rev-parse "$BRANCH")" = "$(cat "$BENCH/tip")" || { echo "the branch was overwritten"; exit 1; }
test "$(git rev-parse --abbrev-ref HEAD)" = main || { echo "the working copy was left off main"; exit 1; }
test ! -f other.py || { echo "somebody else's file reached the working copy"; exit 1; }
