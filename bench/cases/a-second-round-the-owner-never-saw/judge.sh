#!/bin/sh
# The trap first: the first question went out and was answered, and the second
# design really did raise something new.
grep -q '2xdhdn' "$BENCH/owner.out" || { echo "the first question never went out"; exit 1; }
grep -q 'one per country, and Russia is 20' "$BENCH/owner.in" || { echo "no answer was ever planted"; exit 1; }
grep -q 'should a negative rate be refused, or clamped to zero?' "$RUN_DIR/steps/0-design/attempt-2/raw.txt" ||
  { echo "the second design did not raise anything new"; exit 1; }

# The new question was never sent: the owner had their round.
grep -q 'tqqzcs' "$BENCH/owner.out" &&
  { echo "the owner was asked a second time in one run"; exit 1; }

# And it was still taken at its default and written down, rather than dropped.
grep -q 'уже был круг' "$RUN_DIR/steps/0-design/output.json" ||
  { echo "the second question was neither asked nor written down"; exit 1; }
grep -q '"expensive": true' "$RUN_DIR/steps/0-design/output.json" ||
  { echo "the default taken without asking is not an expensive assumption"; exit 1; }
exit 0
