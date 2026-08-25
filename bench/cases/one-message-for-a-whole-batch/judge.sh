#!/bin/sh
# The trap first: the channel was configured, reachable and empty.
test -s "$BENCH/owner-was-clean" || { echo "the channel was not empty when the batch started"; exit 1; }
test -s "$BENCH/owner.out" || { echo "the batch ended and said nothing to anybody"; exit 1; }

# One message, not one per feature. The channel heads each send with its
# number, so this counts sends rather than words: the first version of this
# line counted the batch's name, which every child's own message leaves out —
# and the case was green against a kit where all three of them spoke.
said=$(grep -c '^--- ' "$BENCH/owner.out")
test "$said" = 1 || { echo "the owner was written to $said times for one batch"; exit 1; }
grep -q 'rates' "$BENCH/owner.out" || { echo "the message does not name rates"; exit 1; }
grep -q 'quote' "$BENCH/owner.out" || { echo "the message does not name quote"; exit 1; }
grep -q 'github.com' "$BENCH/owner.out" || { echo "the owner was not told where to read the work"; exit 1; }
exit 0
