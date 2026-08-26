#!/bin/sh
$KIT machine > "$BENCH/after" 2>&1 || { echo "the machine could not be read"; exit 3; }

# The trap first: somebody really was building in the project when the second came.
grep -q 'quote' "$BENCH/after" || { echo "nobody was holding the working copy"; exit 1; }

# The code, not the sentence: 3 stands for more than one refusal, and a
# mechanism that starts naming the wrong one must be caught here.
grep -q 'checkout-held-elsewhere' "$BENCH/kit-said" ||
  { echo "the working copy was held and the refusal did not say so"; exit 1; }

# A machine that is busy does not touch the run it would not start.
test ! -d "$RUN_DIR/steps" ||
  { echo "a second run started a session in a working copy it does not hold"; exit 1; }
test "$(git rev-parse --abbrev-ref HEAD)" = main ||
  { echo "the project was left on somebody's branch"; exit 1; }
test -z "$(git status --porcelain)" ||
  { echo "the project's working copy was written into"; exit 1; }
exit 0
