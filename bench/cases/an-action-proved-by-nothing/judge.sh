#!/bin/sh
# The trap first: this project answers no kind of verification, and the design
# really did name a chore proved by a no-op.
grep -q 'verification' .agent-kit/v3/project.toml &&
  { echo "the trap was not planted: this world answers a kind, so another hook could hold it"; exit 1; }
STEP="$RUN_DIR/steps/0-design"
test -s "$STEP/attempt-1/raw.txt" ||
  { echo "the trap was not planted: the design was never asked"; exit 1; }
grep -q '"proof": "true"' "$STEP/attempt-1/raw.txt" ||
  { echo "the trap was not planted: the design proved nothing with a no-op"; exit 1; }

grep -q 'proof-that-proves-nothing' "$STEP/attempt-1/refusal.txt" ||
  { echo "it was not refused by name: $(cat "$STEP/attempt-1/refusal.txt" 2>/dev/null)"; exit 1; }

# And nothing was written: the chore never reached a file.
test ! -f .agent-kit/v3/manual.md || { echo "a chore nobody could prove was written down"; exit 1; }
exit 0
