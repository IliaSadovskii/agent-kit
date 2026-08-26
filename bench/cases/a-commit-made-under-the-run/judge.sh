#!/bin/sh
# The trap first: the tree really did move, and verify really did write down
# where it stood before it moved.
PROVED=$(sed -n 's/.*"proved_at": "\([0-9a-f]*\)".*/\1/p' "$RUN_DIR/steps/2-verify/output.json")
test -n "$PROVED" || { echo "verify wrote down no commit, so nothing was bound to one"; exit 1; }
test "$PROVED" != "$(git rev-parse HEAD)" ||
  { echo "the trap was not planted: the tree never moved"; exit 1; }

git rev-parse --verify --quiet "$BRANCH" >/dev/null &&
  { echo "a branch was made from a tree nobody measured"; exit 1; }
test -z "$(find "$BENCH" -maxdepth 1 -name 'gh-opened-*' -print -quit)" ||
  { echo "a pull request was opened from a tree nobody measured"; exit 1; }
exit 0
