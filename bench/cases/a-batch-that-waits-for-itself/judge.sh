#!/bin/sh
grep -q 'needs-a-cycle' "$BENCH/kit-said" || { echo "the refusal does not name the code"; exit 1; }
for slug in rates quote receipt; do
  grep -q "$slug" "$BENCH/kit-said" || { echo "the refusal does not name $slug, which is in the loop"; exit 1; }
done
test ! -d "$REPO/.agent-kit/v3/batches" || { echo "a batch was made out of a loop"; exit 1; }
exit 0
