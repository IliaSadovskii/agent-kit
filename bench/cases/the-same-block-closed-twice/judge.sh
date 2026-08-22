#!/bin/sh
KNOWLEDGE=docs/knowledge/entities.md

# The trap: the design named it twice, and there was a block there to close.
grep -c 'k7f3q2' "$RUN_DIR"/steps/*-design/output.json | grep -qv '^1$' ||
  { echo "the design named the identifier once, so nothing was repeated"; exit 1; }
git show main:$KNOWLEDGE 2>/dev/null | grep -q 'id: k7f3q2' ||
  { echo "the block this case closes was never planted"; exit 1; }

grep -q 'id: k7f3q2' "$KNOWLEDGE" && { echo "the block was named twice and closed neither time"; exit 1; }
grep -q '^### Деньги' "$KNOWLEDGE" || { echo "closing took the record with it"; exit 1; }
test "$(grep -c '"closed"' "$RUN_DIR"/steps/*-record/output.json)" = 1 ||
  { echo "the record did not say what it closed"; exit 1; }
git show --name-only --format= HEAD | grep -q "$KNOWLEDGE" ||
  { echo "the closing never reached the commit"; exit 1; }
exit 0
