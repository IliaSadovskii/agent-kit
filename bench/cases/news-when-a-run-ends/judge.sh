#!/bin/sh
# The trap first: nothing was on the channel before the run went.
test -s "$BENCH/owner-was-clean" || { echo "the channel was not empty when the run started"; exit 1; }
test -s "$BENCH/owner.out" || { echo "the run ended and said nothing to anybody"; exit 1; }

grep -q 'add-vat' "$BENCH/owner.out" || { echo "what was said does not name the run"; exit 1; }
grep -q 'done' "$BENCH/owner.out" || { echo "what was said does not say how it ended"; exit 1; }
grep -q 'github.com' "$BENCH/owner.out" || { echo "the owner was not told where to read it"; exit 1; }
exit 0
