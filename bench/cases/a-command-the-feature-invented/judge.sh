#!/bin/sh
# The trap first: this project really does owe the kind, and the design really
# did name a command that cannot fail.
grep -q 'verification.suite' .agent-kit/v3/project.toml ||
  { echo "the trap was not planted: this project answers no kind of verification"; exit 1; }
STEP="$RUN_DIR/steps/0-design"
grep -q '"command": "true"' "$STEP/attempt-1/raw.txt" ||
  { echo "the trap was not planted: the design named no such command"; exit 1; }

grep -q 'command-that-proves-nothing: suite' "$STEP/attempt-1/refusal.txt" ||
  { echo "a command that cannot fail was accepted: $(cat "$STEP/attempt-1/refusal.txt" 2>/dev/null)"; exit 1; }

# And no program ever ran it: the run never reached verify at all.
test ! -d "$RUN_DIR/steps/2-verify" ||
  { echo "verify was reached, so the string was on its way to a shell"; exit 1; }
exit 0
