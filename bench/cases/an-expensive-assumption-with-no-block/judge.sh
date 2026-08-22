#!/bin/sh
# The trap first: a project that keeps no knowledge owes no block, and this
# judge would be green in one. Prove the knowledge was planted and holds the
# record the design would have had to address.
test -s docs/knowledge/entities.md || { echo "no knowledge was planted, so nothing could owe a block"; exit 1; }
grep -q '^`key: money`' docs/knowledge/entities.md || { echo "the planted knowledge holds no record to address"; exit 1; }
if grep -q 'kit/add-vat' docs/knowledge/entities.md; then
  echo "a block was written into the knowledge although the design was refused"; exit 1
fi
exit 0
