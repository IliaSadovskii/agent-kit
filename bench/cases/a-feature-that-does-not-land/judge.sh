#!/bin/sh
BATCHES="$REPO/.agent-kit/v3/batches/vat/batch.json"
# The trap first: rates really was refused, over and over, rather than skipped.
grep -q '"status": "failed"' "$BATCHES" || { echo "nothing failed, so nothing was cascaded from"; exit 1; }

grep -q 'needed-rates' "$BATCHES" || { echo "quote does not say what it was waiting for"; exit 1; }
test ! -d "$REPO/.agent-kit/v3/runs/quote" || { echo "a run was started for a feature that could not be built"; exit 1; }
test ! -d "$REPO/.agent-kit/v3/trees/quote" || { echo "a tree was made for it"; exit 1; }
# Commits the trunk does not have: a branch made by `worktree add` already
# carries main's history, so "it has a commit" is true before anything is built.
test "$(git rev-list --count main..kit/receipt)" -ge 1 ||
  { echo "the feature that needed nothing did not land"; exit 1; }
exit 0
