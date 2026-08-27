#!/bin/sh
# The trap first: the reading really did come back with a contradiction, and
# the case really did script nobody to answer it.
grep -q '"contradicts"' "$SITTINGS"/*/steps/0-reading/output.json ||
  { echo "the trap was not planted: nothing contradicted anything"; exit 1; }
# The shape a question is printed in, and not a question mark anywhere in the
# output: half the prose the kit prints has one.
test "$(grep -c '^? ' "$BENCH/kit-said")" -eq 1 ||
  { echo "the trap was not planted: the question was never put to anybody"; exit 1; }

grep -q 'nobody-to-ask' "$BENCH/kit-said" ||
  { echo "refused, and not for the missing answer: $(tail -1 "$BENCH/kit-said")"; exit 1; }
# `nobody answered` is a different sentence from `no channel`, and both are
# different from the night's twenty minutes. This one has its own code.
grep -q 'nobody-answered\|no-channel' "$BENCH/kit-said" &&
  { echo "a sitting reported itself as a night that nobody answered"; exit 1; }

# Nothing written: half a description is worse than none.
grep -q 'сумма, ставка и валюта' docs/knowledge/product.md &&
  { echo "the description was written with the contradiction unsettled"; exit 1; }
test -d "$SITTINGS" || { echo "the sitting left no paperwork at all"; exit 1; }
test -s "$SITTINGS"/*/telling.txt || { echo "what the owner said was not kept"; exit 1; }
exit 0
