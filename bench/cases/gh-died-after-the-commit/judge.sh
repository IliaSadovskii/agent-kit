#!/bin/sh
# The trap first: an earlier delivery really did leave a commit on the branch,
# and what the run ended on is that same commit. Without this the judge is
# green against an ordinary night, which lands one commit and one pull request
# just the same.
test -s "$BENCH/planted" || { echo "no earlier delivery was planted, so nothing was carried on"; exit 1; }
test "$(git rev-parse "$BRANCH")" = "$(cat "$BENCH/planted")" ||
  { echo "the commit was made again rather than carried on"; exit 1; }

test "$(git rev-list --count "main..$BRANCH")" = 1 || { echo "the work was committed twice: $(git rev-list --count "main..$BRANCH") commits"; exit 1; }
grep -q "pull_request" "$RUN_DIR"/steps/*-deliver/output.json || { echo "no pull request was recorded"; exit 1; }
