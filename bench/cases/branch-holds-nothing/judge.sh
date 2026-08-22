#!/bin/sh
test "$(git rev-list --count "main..$BRANCH")" = 1 || { echo "the branch does not hold exactly this work"; exit 1; }
git ls-remote --heads origin | grep -q "$BRANCH" || { echo "the branch never reached the remote"; exit 1; }
