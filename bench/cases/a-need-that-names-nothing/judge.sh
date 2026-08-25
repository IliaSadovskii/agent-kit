#!/bin/sh
grep -q 'no-such-feature' "$BENCH/kit-said" ||
  { echo "the refusal does not name the code a script would read"; exit 1; }
test ! -d "$REPO/.agent-kit/v3/batches" || { echo "a batch was made out of a graph that cannot run"; exit 1; }
test ! -d "$REPO/.agent-kit/v3/runs/quote" || { echo "a run was created for it"; exit 1; }
test ! -d "$REPO/.agent-kit/v3/trees" || { echo "a tree was made for it"; exit 1; }
exit 0
