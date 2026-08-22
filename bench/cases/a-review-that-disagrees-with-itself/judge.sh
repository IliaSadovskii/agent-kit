#!/bin/sh
test "$(git rev-parse --abbrev-ref HEAD)" = main || { echo "the working copy was left off main"; exit 1; }
git rev-parse --verify --quiet "$BRANCH" >/dev/null && { echo "work was branched on a refused review"; exit 1; }

# The disagreement is caught by `record` now, before the owner's knowledge is
# touched. That is only a claim while there is knowledge here to spare.
KNOWLEDGE=docs/knowledge/entities.md
test -s "$KNOWLEDGE" || { echo "no knowledge was planted, so nothing could have been spared"; exit 1; }
grep -q "id: k7f3q2" "$KNOWLEDGE" || { echo "the planted knowledge holds no block to spare"; exit 1; }
test "$(git status --porcelain -- "$KNOWLEDGE")" = "" || { echo "the run edited the knowledge before it refused"; exit 1; }
grep -q "kit/add-vat" "$KNOWLEDGE" && { echo "a block reached the knowledge although the run refused"; exit 1; }
exit 0
