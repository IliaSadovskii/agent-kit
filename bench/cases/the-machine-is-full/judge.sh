#!/bin/sh
# The trap first: the machine really was full when the run asked.
$KIT machine > "$BENCH/after" 2>&1 || { echo "the machine could not be read"; exit 3; }
grep -q 'somebody-else' "$BENCH/after" || { echo "nothing was holding the machine at all"; exit 1; }

# And nothing was paid for: a refused run has no session and no attempt.
# The code, not the exit status: 3 and 4 each stand for more than one refusal,
# and a mechanism that starts naming the wrong one must be caught here.
grep -q 'no-slot' "$BENCH/kit-said" || { echo "the machine was full and the refusal did not say so"; exit 1; }

test ! -d "$RUN_DIR/steps" || { echo "a session was started on a machine that was full"; exit 1; }
exit 0
