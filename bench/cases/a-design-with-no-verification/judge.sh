#!/bin/sh
# The trap first: this project really does check itself for a kind, so a design
# of a feature of it really does owe a record. A world that answered no kind
# would make both halves below green for a design that owes nothing.
grep -q 'verification.suite' .agent-kit/v3/project.toml ||
  { echo "the trap was not planted: this project answers no kind of verification"; exit 1; }

# Both halves of the trap, each in the attempt it was planted in: the field
# absent, and then the field there and answering nothing. A judge that reads
# only the last refusal is green against a kit that knows one of the two.
STEP="$RUN_DIR/steps/0-design"
grep -q 'output-missing-field: proves' "$STEP/attempt-1/refusal.txt" ||
  { echo "a design that never returned the field was not refused for it"; exit 1; }
grep -q '"proves": \[\]' "$STEP/attempt-2/raw.txt" ||
  { echo "the trap was not planted: the second attempt never answered nothing"; exit 1; }
grep -q 'output-empty-field: proves' "$STEP/attempt-2/refusal.txt" ||
  { echo "a design that will prove nothing was not refused for it"; exit 1; }
exit 0
