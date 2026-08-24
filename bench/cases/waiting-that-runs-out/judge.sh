#!/bin/sh
test -s "$BENCH/planted-at" || { echo "nothing was planted, so nothing was waited for"; exit 1; }
grep -q 'no-slot' "$BENCH/kit-said" || { echo "the refusal does not name a slot"; exit 1; }

# It waited before it gave up. Without this the case is green against a kit
# that refuses at once, which is the other half of what `wait` means.
WAITED=$(( $(date +%s) - $(cat "$BENCH/planted-at") ))
test "$WAITED" -ge 4 || { echo "the whole run took ${WAITED}s, so it never waited its five"; exit 1; }
test ! -d "$RUN_DIR/steps" || { echo "a session was started on a machine that stayed full"; exit 1; }
exit 0
