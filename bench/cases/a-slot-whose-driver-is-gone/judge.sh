#!/bin/sh
# The trap first: the machine was full before the run, and full of a ghost.
grep -q 'a-ghost' "$BENCH/before" || { echo "no dead lease was ever planted"; exit 1; }

# Reading the ledger through any command sweeps the ghost away, so "it is gone
# afterwards" is true whatever the kit does and says nothing. What discriminates
# is that the run got a slot at all: with the lease standing it exits 4.
grep -q 'no-slot' "$BENCH/kit-said" && { echo "the dead lease held the machine up"; exit 1; }
test -f "$RUN_DIR/steps/0-design/output.json" || { echo "the design step produced nothing"; exit 1; }
exit 0
