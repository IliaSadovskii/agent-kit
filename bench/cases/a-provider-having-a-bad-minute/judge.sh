#!/bin/sh
# The trap first: two sessions really were turned away by the tool. A judge
# that reads only what the kit printed is green in a night where nothing was
# ever refused, and there is nothing to pause between.
for attempt in 1 2; do
  said="$RUN_DIR/steps/0-design/attempt-$attempt/refusal.txt"
  test -s "$said" || { echo "attempt $attempt of the design was never refused"; exit 1; }
  grep -q 'session-died' "$said" || { echo "attempt $attempt was refused by something else: $(cat "$said")"; exit 1; }
done
test -f "$RUN_DIR/steps/0-design/output.json" || { echo "the design never got its answer"; exit 1; }

# And then the mechanism: it did not go straight back round, and it waited
# longer the second time. The seconds are the ones this case planted.
grep -q 'backing-off 1s' "$BENCH/kit-said" || { echo "the first refusal was followed by no pause"; exit 1; }
grep -q 'backing-off 2s' "$BENCH/kit-said" || { echo "the pause did not grow with the attempt"; exit 1; }
exit 0
