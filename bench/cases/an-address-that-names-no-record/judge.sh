#!/bin/sh
test -s docs/knowledge/entities.md || { echo "no knowledge was planted, so no address could fail to resolve"; exit 1; }
grep -q '^### Деньги' docs/knowledge/entities.md || { echo "the planted knowledge holds no record at all"; exit 1; }
if grep -q 'ghost' docs/knowledge/entities.md; then
  echo "the knowledge does hold the record the case says it does not"; exit 1
fi
if grep -q 'kit/add-vat' docs/knowledge/entities.md; then
  echo "a block was written although its address resolved to nothing"; exit 1
fi
exit 0
