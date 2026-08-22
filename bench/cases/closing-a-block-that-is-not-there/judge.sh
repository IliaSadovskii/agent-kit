#!/bin/sh
# The trap: a knowledge that holds a real block with a real identifier, so that
# "nothing was deleted" is a statement about a refusal and not about an empty file.
test -s docs/knowledge/entities.md || { echo "no knowledge was planted, so nothing could be closed"; exit 1; }
grep -q 'id: k7f3q2' docs/knowledge/entities.md || { echo "the planted knowledge holds no block with an identifier"; exit 1; }
if grep -q 'zzzzzz' docs/knowledge/entities.md; then
  echo "the knowledge does hold the identifier the case says it does not"; exit 1
fi
exit 0
