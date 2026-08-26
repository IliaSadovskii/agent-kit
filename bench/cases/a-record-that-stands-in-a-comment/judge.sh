#!/bin/sh
KNOWLEDGE=docs/knowledge/entities.md

# The trap first: the record the design addresses really is written down, and
# really does stand inside an HTML comment — which is where all six of the
# second version's templates keep their example. Without this the refusal would
# be about a key nobody wrote, and that is a different mechanism.
test -s "$KNOWLEDGE" || { echo "no knowledge was planted at all"; exit 1; }
grep -q '^`key: offer`' "$KNOWLEDGE" || { echo "the trap was not planted: no such key is written"; exit 1; }
awk '/<!--/{c=1} /-->/{c=0} c && /^`key: offer`/{found=1} END{exit !found}' "$KNOWLEDGE" ||
  { echo "the trap was not planted: the key does not stand inside a comment"; exit 1; }
grep -q '^`key: money`' "$KNOWLEDGE" || { echo "the knowledge holds no record outside the comment"; exit 1; }

# And nothing was written: not into the comment, and not anywhere else.
if grep -q 'kit/add-vat' "$KNOWLEDGE"; then
  echo "a block was written although its address stands only inside a comment"; exit 1
fi
exit 0
