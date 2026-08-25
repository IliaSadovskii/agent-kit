#!/bin/sh
BATCHES="$REPO/.agent-kit/v3/batches/vat/batch.json"
# The trap first: the skip was asked for from inside the night, and it reached
# this run as a stop while its own session was still alive.
test -s "$BENCH/skip-said" || { echo "nothing ever asked for a skip"; exit 1; }
grep -q 'skip-asked' "$BENCH/skip-said" ||
  { echo "the skip did not reach the driver holding the batch: $(cat "$BENCH/skip-said")"; exit 1; }
test -s "$BENCH/quote-saw-the-stop" || { echo "the skip never became a stop against the running feature"; exit 1; }

grep -q 'needed-quote' "$BATCHES" || { echo "receipt does not say which feature took it with it"; exit 1; }
test ! -d "$REPO/.agent-kit/v3/runs/receipt" || { echo "a run was started for what needed a skipped feature"; exit 1; }
test "$(git rev-list --count main..kit/quote 2>/dev/null || echo 0)" -eq 0 ||
  { echo "a skipped feature was delivered anyway"; exit 1; }
test "$(git rev-list --count main..kit/rates)" -ge 1 || { echo "the rest of the night did not land"; exit 1; }
exit 0
