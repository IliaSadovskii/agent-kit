#!/bin/sh
$KIT machine > "$BENCH/after" 2>&1 || { echo "the machine could not be read"; exit 3; }
grep -q "$SLUG" "$BENCH/after" || { echo "nobody was holding the run when the second driver came"; exit 1; }

# The code, not the exit status: 3 and 4 each stand for more than one refusal,
# and a mechanism that starts naming the wrong one must be caught here.
grep -q 'run-held-elsewhere' "$BENCH/kit-said" || { echo "the run was held elsewhere and the refusal did not say so"; exit 1; }

test ! -d "$RUN_DIR/steps" || { echo "a second driver started a session on a run it does not hold"; exit 1; }
exit 0
