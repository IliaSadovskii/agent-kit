#!/bin/sh
$KIT machine > "$BENCH/after" 2>&1 || { echo "the machine could not be read"; exit 3; }
grep -q "$SLUG" "$BENCH/after" || { echo "nobody was holding the run when the second driver came"; exit 1; }

test ! -d "$RUN_DIR/steps" || { echo "a second driver started a session on a run it does not hold"; exit 1; }
exit 0
