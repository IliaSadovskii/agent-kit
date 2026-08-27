#!/bin/sh
# The trap first: there really is a part standing that the reading never named.
grep -q 'key: money' docs/knowledge/product.md ||
  { echo "the trap was not planted: this project has no part to drop"; exit 1; }
grep -q '"money"' "$SITTINGS"/*/steps/0-reading/attempt-1/raw.txt &&
  { echo "the trap was not planted: the reading did answer for it"; exit 1; }

grep -q 'reading-misses-a-part' "$BENCH/kit-said" ||
  { echo "refused, and not for the missing part: $(tail -1 "$BENCH/kit-said")"; exit 1; }
grep -q 'money' "$BENCH/kit-said" ||
  { echo "the refusal does not name which part was dropped"; exit 1; }
grep -q 'уведомления' docs/knowledge/product.md &&
  { echo "half a reading was written into the description"; exit 1; }
exit 0
