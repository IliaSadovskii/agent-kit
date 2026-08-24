#!/bin/sh
# The trap first: a stray answer was standing, and this run's question went out.
grep -q 'zzzzzz' "$BENCH/owner.in" || { echo "no stray answer was ever planted"; exit 1; }
grep -q '2xdhdn' "$BENCH/owner.out" || { echo "this run's question never went out"; exit 1; }

grep -q '"how": "nobody-answered"' "$RUN_DIR/steps/0-design/asks.json" ||
  { echo "the stray answer was taken for this question's"; exit 1; }
test ! -d "$RUN_DIR/steps/0-design/attempt-2" ||
  { echo "the design was run again on an answer that was not addressed to it"; exit 1; }
grep -q 'A-STRAY-ANSWER' "$RUN_DIR/steps/0-design/output.json" &&
  { echo "the stray answer reached the design"; exit 1; }
exit 0
