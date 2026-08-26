#!/bin/sh
# The ordinary run above went through, and it is the trap's other half: the
# refusals below have to be about the order and not about every run.
grep -q '"status": "done"' "$RUN_DIR/run.json" ||
  { echo "the run in the ordinary order did not reach its end"; exit 1; }

# A verify before the build it would measure. Green by construction, and every
# later reader sees passed: true.
$KIT run new backwards --brief "Money should quote VAT" \
  --steps design,verify,build,review,record,deliver > "$BENCH/backwards" 2>&1
test "$?" = 3 || { echo "a verify before its build was created: $(cat "$BENCH/backwards")"; exit 1; }
grep -q 'steps-out-of-order' "$BENCH/backwards" ||
  { echo "it was refused, and not because of the order: $(cat "$BENCH/backwards")"; exit 1; }
test ! -f "$REPO/.agent-kit/v3/runs/backwards/run.json" ||
  { echo "the refused run was written down anyway"; exit 1; }

# And the same step twice.
$KIT run new twice --brief "Money should quote VAT" --steps verify,verify > "$BENCH/twice" 2>&1
test "$?" = 3 || { echo "a step asked for twice was created: $(cat "$BENCH/twice")"; exit 1; }
grep -q 'step-twice' "$BENCH/twice" ||
  { echo "it was refused, and not because the step is asked for twice: $(cat "$BENCH/twice")"; exit 1; }

# What the kit itself asks for is still a run: this refuses an order, not runs.
$KIT run new plain --brief "Money should quote VAT" --steps design,build > "$BENCH/plain" 2>&1
test "$?" = 0 || { echo "a run in its own order was refused too: $(cat "$BENCH/plain")"; exit 1; }
exit 0
