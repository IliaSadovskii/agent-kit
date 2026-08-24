#!/bin/sh
$KIT machine > "$BENCH/after" 2>&1 || { echo "the machine could not be read"; exit 3; }
grep -q '2027-01-01' "$BENCH/after" || { echo "no limit was standing when the run asked"; exit 1; }
grep -q 'another/build' "$BENCH/after" || { echo "the standing limit is not the one that was planted"; exit 1; }

test ! -d "$RUN_DIR/steps" || { echo "a session was paid for against a limited account"; exit 1; }
exit 0
