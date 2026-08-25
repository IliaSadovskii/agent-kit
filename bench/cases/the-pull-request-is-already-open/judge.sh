#!/bin/sh
test -f "$BENCH/gh-opened-$(printf '%s' "$BRANCH" | tr / -)" || { echo "no pull request was open to find"; exit 1; }
created=$(grep -c "^create$" "$BENCH/gh-argv" || true)
test "$created" = 0 || { echo "a second pull request was opened over the standing one"; exit 1; }
grep -q "pull_request" "$RUN_DIR"/steps/*-deliver/output.json || { echo "the standing pull request was not recorded"; exit 1; }
