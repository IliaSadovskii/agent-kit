#!/bin/sh
KNOWLEDGE=docs/knowledge/entities.md
# The trap: two blocks really did touch, with no blank line between them.
BEFORE="$(git show main:$KNOWLEDGE 2>/dev/null)" || { echo "no knowledge was planted"; exit 1; }
printf '%s\n' "$BEFORE" | grep -A1 'id: k7f3q2' | grep -q 'id: m4tp8v' ||
  { echo "the two blocks were not planted touching, so nothing could be taken with the first"; exit 1; }

grep -q 'id: k7f3q2' "$KNOWLEDGE" && { echo "the block the design closed is still there"; exit 1; }
grep -q 'id: m4tp8v' "$KNOWLEDGE" || { echo "closing the first block took its neighbour with it"; exit 1; }
grep -q 'Валюта всегда одна' "$KNOWLEDGE" || { echo "the neighbour lost its body"; exit 1; }
exit 0
