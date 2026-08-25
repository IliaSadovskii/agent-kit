#!/bin/sh
# The trap first: somebody else really was in the queue, on another account,
# and the machine really was full when this run arrived.
grep -q 'asked-first' "$BENCH/before" || { echo "no older waiter was ever planted"; exit 1; }
grep -q 'somebody-else' "$BENCH/before" || { echo "the machine was not full when the run arrived"; exit 1; }

# The lease was three seconds and the wait was eight, so what refused this run
# is the queue rather than the ceiling: it outlived the thing holding the slot.
grep -q 'no-slot' "$BENCH/kit-said" || { echo "the run was refused by something other than the queue"; exit 1; }
grep -q 'asked-first' "$BENCH/kit-said" ||
  { echo "the refusal does not name who is in front, so it took the slot over their head"; exit 1; }
exit 0
