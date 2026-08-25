#!/bin/sh
RUNS="$REPO/.agent-kit/v3/runs"
# The trap first: rates really did land, so there was something to wait for.
git log kit/rates --format=%s | grep -q . || { echo "rates never landed at all"; exit 1; }

# What quote was shown. Reading is never an instruction, so what it needs is in
# the input the driver composed, and this is the word only rates ever wrote.
grep -rq 'TABLE-OF-RATES' "$RUNS/quote/steps/0-design/attempt-1/input.md" ||
  { echo "quote was never shown what rates designed"; exit 1; }
exit 0
