#!/bin/sh
KNOWLEDGE=docs/knowledge/entities.md

# The trap: the design really did word two expensive assumptions the same, and
# the knowledge really was there to write both into. Without both halves this
# judge is green against a run that had one assumption and one block.
DESIGN="$(cat "$RUN_DIR"/steps/*-design/output.json)"
test "$(printf '%s' "$DESIGN" | grep -c 'everything here is a whole number')" -ge 2 ||
  { echo "the design did not word two assumptions the same"; exit 1; }
git show main:$KNOWLEDGE 2>/dev/null | grep -q '^### Скидка' ||
  { echo "the second record the case writes into was never planted"; exit 1; }

test "$(grep -c 'kit/add-vat' "$KNOWLEDGE")" = 2 ||
  { echo "the two assumptions did not leave two blocks: $(grep -c 'kit/add-vat' "$KNOWLEDGE") of 2"; exit 1; }

# Two blocks, and two names. One name written twice is one block, whatever the
# record says it wrote.
NAMES="$(grep -o 'id: [a-z0-9]*' "$KNOWLEDGE" | grep -v k7f3q2 | sort -u | wc -l)"
test "$NAMES" = 2 || { echo "the two blocks carry $NAMES distinct identifiers, not 2"; exit 1; }

# And each under the record it addressed.
awk '/^### Налог/{seen=1; next} /^### /{seen=0} seen && /kit\/add-vat/{found=1} END{exit !found}' "$KNOWLEDGE" ||
  { echo "nothing was written under the first record addressed"; exit 1; }
awk '/^### Скидка/{seen=1; next} /^### /{seen=0} seen && /kit\/add-vat/{found=1} END{exit !found}' "$KNOWLEDGE" ||
  { echo "nothing was written under the second record addressed"; exit 1; }

# What the step reported has to be what the file holds.
test "$(grep -c '"id"' "$RUN_DIR"/steps/*-record/output.json)" = 2 ||
  { echo "the record did not report two blocks"; exit 1; }
exit 0
