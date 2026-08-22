#!/bin/sh
# The branch half, as it always was.
git rev-parse --verify --quiet "$BRANCH" >/dev/null && { echo "blocked work was branched anyway"; exit 1; }
test ! -f "$BENCH/gh-opened" || { echo "a pull request was opened for blocked work"; exit 1; }

# And the knowledge half, which this case only started promising when the
# deliverable question moved in front of `record`. A judge asserting "the
# knowledge is untouched" is green in a project that keeps none, so the trap
# has to be shown standing before it is judged.
KNOWLEDGE=docs/knowledge/entities.md
test -s "$KNOWLEDGE" || { echo "no knowledge was planted, so nothing could have been spared"; exit 1; }
grep -q "id: k7f3q2" "$KNOWLEDGE" || { echo "the planted knowledge holds no block to spare"; exit 1; }
test "$(git status --porcelain -- "$KNOWLEDGE")" = "" || { echo "the run edited the knowledge before it refused"; exit 1; }
grep -q "kit/add-vat" "$KNOWLEDGE" && { echo "a block reached the knowledge although the run refused"; exit 1; }
exit 0
