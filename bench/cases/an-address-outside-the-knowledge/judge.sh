#!/bin/sh
# The trap: the file the design addresses really is there, and really is not
# knowledge. Without it the refusal would be about a missing file, which is a
# different mechanism, and this judge would be green for the wrong reason.
test -s docs/knowledge/notes.txt || { echo "the file the design addresses was never planted"; exit 1; }
test -s docs/knowledge/entities.md || { echo "no knowledge was planted at all"; exit 1; }
grep -q 'kit/add-vat' docs/knowledge/notes.txt && { echo "a block was written where nothing can read it"; exit 1; }
grep -q 'kit/add-vat' docs/knowledge/entities.md && { echo "a block was written after the address was refused"; exit 1; }
exit 0
