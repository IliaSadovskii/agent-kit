#!/bin/sh
test "$(git rev-list --count "main..$BRANCH")" = 1 || { echo "the work was committed twice: $(git rev-list --count "main..$BRANCH") commits"; exit 1; }
grep -q "pull_request" "$RUN_DIR/steps/4-deliver/output.json" || { echo "no pull request was recorded"; exit 1; }
