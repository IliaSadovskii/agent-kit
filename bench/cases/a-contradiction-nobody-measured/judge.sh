#!/bin/sh
# The trap first: the review really did name a file, and that file really is
# not one the project's commands were measured over.
REVIEW="$RUN_DIR/steps/3-review"
grep -q 'invented.py' "$REVIEW/attempt-1/raw.txt" ||
  { echo "the trap was not planted: the review named no invented file"; exit 1; }
grep -q 'invented.py' "$RUN_DIR/steps/2-verify/output.json" &&
  { echo "the trap was not planted: the file was measured after all"; exit 1; }

grep -q 'where-nobody-measured' "$REVIEW/attempt-1/refusal.txt" ||
  { echo "an invented contradiction was accepted: $(cat "$REVIEW/attempt-1/refusal.txt" 2>/dev/null)"; exit 1; }
# Refused as an answer and asked again, never acted on: the run must not carry
# the code a substantiated contradiction stops it by.
grep -q 'why-the-diff-contradicts: types' "$RUN_DIR/run.json" &&
  { echo "a contradiction nobody measured was acted on"; exit 1; }
exit 0
