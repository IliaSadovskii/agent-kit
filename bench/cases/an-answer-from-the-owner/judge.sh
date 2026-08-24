#!/bin/sh
# The trap first: the question went out and the answer was standing before it did.
test -s "$BENCH/owner.out" || { echo "no question ever went to the owner"; exit 1; }
grep -q 'one VAT rate for everything, or one per country?' "$BENCH/owner.out" || { echo "what went out is not the question the design asked"; exit 1; }
grep -q 'one per country, and Russia is 20' "$BENCH/owner.in" || { echo "no answer was ever planted"; exit 1; }

grep -q '"how": "answered"' "$RUN_DIR/steps/0-design/asks.json" ||
  { echo "the answer was not read"; exit 1; }

# Run again, with what they said enclosed — not merely handed to the next step.
test -d "$RUN_DIR/steps/0-design/attempt-2" || { echo "the design was not run again"; exit 1; }
grep -q 'one per country, and Russia is 20' "$RUN_DIR/steps/0-design/attempt-2/input.md" ||
  { echo "the second attempt was not given the answer"; exit 1; }

# And what is on file is what the answer said, not the default.
grep -q 'as the owner said' "$RUN_DIR/steps/0-design/output.json" ||
  { echo "the design on file is not the one the answer produced"; exit 1; }
grep -q 'nobody-answered' "$RUN_DIR/steps/0-design/asks.json" &&
  { echo "a default was taken for a question that was answered"; exit 1; }
exit 0
