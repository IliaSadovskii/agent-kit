#!/bin/sh
# The trap first: the project really does answer a kind without deciding anything.
grep -q 'verification.types' .agent-kit/v3/project.toml ||
  { echo "the trap was not planted: no kind is answered at all"; exit 1; }
grep -q '^since' .agent-kit/v3/project.toml &&
  { echo "the trap was not planted: the refusal carries a date after all"; exit 1; }

grep -q 'bad-verification-answer' "$BENCH/kit-said" ||
  { echo "the answer was not refused by name: $(tail -1 "$BENCH/kit-said")"; exit 1; }
exit 0
