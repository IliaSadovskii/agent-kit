#!/bin/sh
$KIT machine > "$BENCH/after" 2>&1 || { echo "the machine could not be read"; exit 3; }
grep -q 'somebody-else' "$BENCH/after" || { echo "nothing was holding the provider at all"; exit 1; }

grep -q 'no-slot' "$BENCH/kit-said" || { echo "the refusal does not name a slot"; exit 1; }
# And it says which ceiling, because "the machine is full" would be a lie: it
# has three free seats and none of them are on this provider. What tells the two
# refusals apart is the provider's own name: the machine-wide one is about the
# machine and names nobody. Measured that way rather than by the sentence
# `fake runs`, which was English prose and went red on the translation alone.
grep 'no-slot' "$BENCH/kit-said" | grep -q 'fake' ||
  { echo "the refusal blames the machine, not the provider"; exit 1; }
test ! -d "$RUN_DIR/steps" || { echo "a session was started past the provider's own ceiling"; exit 1; }
exit 0
