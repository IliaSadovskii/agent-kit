#!/bin/sh
$KIT machine > "$BENCH/after" 2>&1 || { echo "the machine could not be read"; exit 3; }
grep -q '2027-01-01' "$BENCH/after" || { echo "no limit was standing when the run asked"; exit 1; }
grep -q 'another/build' "$BENCH/after" || { echo "the standing limit is not the one that was planted"; exit 1; }

# The code, not the exit status: 3 and 4 each stand for more than one refusal,
# and a mechanism that starts naming the wrong one must be caught here.
grep -q 'provider-limited' "$BENCH/kit-said" || { echo "the account was limited and the refusal did not say so"; exit 1; }

test ! -d "$RUN_DIR/steps" || { echo "a session was paid for against a limited account"; exit 1; }
exit 0
