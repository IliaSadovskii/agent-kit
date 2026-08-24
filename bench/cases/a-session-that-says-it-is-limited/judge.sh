#!/bin/sh
# The trap first: the session really did refuse, and refused for this reason.
grep -q 'provider-limited' "$RUN_DIR/run.json" || { echo "no session ever said it was limited"; exit 1; }

$KIT machine > "$BENCH/after" 2>&1 || { echo "the machine could not be read"; exit 3; }
grep -q '2027-01-01' "$BENCH/after" ||
  { echo "the limit died with the session that paid to find it"; exit 1; }
# And it says who found out, which is what proves it came from the run rather
# than from anything the case planted.
grep -q "$SLUG/design" "$BENCH/after" || { echo "the limit does not say which run found it"; exit 1; }
exit 0
