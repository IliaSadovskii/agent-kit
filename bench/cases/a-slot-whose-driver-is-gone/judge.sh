#!/bin/sh
# The trap first: the machine was full before the run, and full of a ghost.
grep -q 'a-ghost' "$BENCH/before" || { echo "no dead lease was ever planted"; exit 1; }

# It is gone now, and it was not the run that gave it back.
$KIT machine > "$BENCH/after" 2>&1 || { echo "the machine could not be read"; exit 3; }
grep -q 'a-ghost' "$BENCH/after" && { echo "the dead lease is still holding the machine"; exit 1; }
test -f "$RUN_DIR/steps/0-design/output.json" || { echo "the design step produced nothing"; exit 1; }
exit 0
