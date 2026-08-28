#!/bin/sh
# The trap first: this project really does check itself for two kinds, and the
# design really did answer the way this case plants.
grep -q 'verification.types' .agent-kit/v3/project.toml ||
  { echo "the trap was not planted: this project answers no kind of verification"; exit 1; }
STEP="$RUN_DIR/steps/0-design"
test -s "$STEP/attempt-1/raw.txt" ||
  { echo "the trap was not planted: the design was never asked"; exit 1; }
grep -q '"types"' "$STEP/attempt-1/raw.txt" &&
  { echo "the trap was not planted: the design did answer for types"; exit 1; }

grep -q 'kind-unproved: types' "$STEP/attempt-1/refusal.txt" ||
  { echo "silence about a kind was not refused: $(cat "$STEP/attempt-1/refusal.txt" 2>/dev/null)"; exit 1; }
exit 0
