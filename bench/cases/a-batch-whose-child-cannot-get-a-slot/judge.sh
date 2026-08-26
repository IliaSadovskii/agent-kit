#!/bin/sh
# The trap first: the machine really was full, and the child really did ask.
$KIT machine > "$BENCH/after" 2>&1 || { echo "the machine could not be read"; exit 3; }
grep -q 'somebody-else' "$BENCH/after" || { echo "nothing was holding the machine at all"; exit 1; }
grep -q 'no-slot' "$REPO/.agent-kit/v3/runs/rates/driver.log" ||
  { echo "the child never got as far as being turned away"; exit 1; }

# Nothing was paid for and nothing was moved: the run is where it was left.
test ! -d "$REPO/.agent-kit/v3/runs/rates/steps" ||
  { echo "a session was started on a machine that was full"; exit 1; }

# And the night can be carried on, which is measured by carrying it on. The
# machine is given back, and what the batch would not pick up again is a
# feature this case has already lost.
CASE=$(dirname "$0")
$KIT slot release --slug somebody-else || { echo "the slot could not be given back"; exit 3; }
$KIT -C "$REPO" batch go vat --provider fake \
  --option rates:reply="$CASE/replies/rates/01-design.json" \
  --option rates:reply="$CASE/replies/rates/02-build.json" \
  --option rates:reply="$CASE/replies/rates/03-review.json" > "$BENCH/second-go" 2>&1 ||
  { echo "the batch did not carry on: $(tail -n 2 "$BENCH/second-go" | tr '\n' ' ')"; exit 1; }
grep -q '"status": "done"' "$BATCH_FILE" ||
  { echo "the feature the machine turned away never landed"; exit 1; }
exit 0
