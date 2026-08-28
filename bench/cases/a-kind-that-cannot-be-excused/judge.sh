#!/bin/sh
# The trap first: this project really does check itself for two kinds, and the
# design really did answer the way this case plants.
grep -q 'verification.types' .agent-kit/v3/project.toml ||
  { echo "the trap was not planted: this project answers no kind of verification"; exit 1; }
STEP="$RUN_DIR/steps/0-design"
test -s "$STEP/attempt-1/raw.txt" ||
  { echo "the trap was not planted: the design was never asked"; exit 1; }
grep -q 'тут нечего тестировать' "$STEP/attempt-1/raw.txt" ||
  { echo "the trap was not planted: the design excused nothing"; exit 1; }

grep -q 'kind-cannot-be-excused: suite' "$STEP/attempt-1/refusal.txt" ||
  { echo "the excuse was not refused: $(cat "$STEP/attempt-1/refusal.txt" 2>/dev/null)"; exit 1; }
exit 0
