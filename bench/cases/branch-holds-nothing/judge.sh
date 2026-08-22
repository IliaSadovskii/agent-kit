#!/bin/sh
test -f "$BENCH/planted" || { echo "the branch was never planted, so nothing was reused"; exit 1; }
test "$(git rev-list --count "main..$BRANCH")" = 1 || { echo "the branch does not hold exactly this work"; exit 1; }
git ls-remote --heads origin | grep -q "$BRANCH" || { echo "the branch never reached the remote"; exit 1; }
# The commit sits on top of what was planted, so the branch was used and not remade.
git merge-base --is-ancestor "$(cat "$BENCH/planted")" "$BRANCH" || { echo "the branch was made again rather than used"; exit 1; }
