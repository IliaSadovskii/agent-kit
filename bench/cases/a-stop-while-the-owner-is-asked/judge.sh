#!/bin/sh
# The trap first: the stop was asked for, and it went to the driver.
test -s "$BENCH/stop-said" || { echo "nothing ever asked this run to stop"; exit 1; }
grep -q '^stop-asked:' "$BENCH/stop-said" ||
  { echo "the stop was written into the state under a driver that holds it"; exit 1; }

# And it was really waiting on a person when it was stopped.
grep -q '2xdhdn' "$BENCH/owner.out" || { echo "the run was not waiting on the owner at all"; exit 1; }
test ! -e "$BENCH/owner.in" || { echo "an answer was standing, so this measured the answer"; exit 1; }

# It stopped where it was, rather than waiting out its ten minutes.
test ! -d "$RUN_DIR/steps/1-build" || { echo "a step ran after the run was told to stop"; exit 1; }
test ! -f "$BENCH/gh-opened" || { echo "a pull request was opened for a run that was stopped"; exit 1; }
exit 0
