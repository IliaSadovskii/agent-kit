#!/bin/sh
FILE=.agent-kit/v3/manual.md

# The trap first: the old ignore really stands, it really covers this file, and
# the design really did name a chore. Without all three, "nothing was written"
# is green in a world where nothing was ever asked for.
test -f .agent-kit/v3/.gitignore || { echo "the trap was not planted: no old ignore"; exit 1; }
git check-ignore -q "$FILE" || { echo "the trap was not planted: the file is not ignored here"; exit 1; }
grep -q 'STRIPE_KEY' .agent-kit/v3/runs/rates/steps/0-design/output.json ||
  { echo "the trap was not planted: nothing needed doing by hand"; exit 1; }

grep -q 'manual-ignored' "$BENCH/kit-said" ||
  { echo "the file was hidden and nobody said so: $(tail -3 "$BENCH/kit-said")"; exit 1; }
test ! -f "$FILE" ||
  { echo "the chore was written into a file the repository throws away"; exit 1; }
exit 0
