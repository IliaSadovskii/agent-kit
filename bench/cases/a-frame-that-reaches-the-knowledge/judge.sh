#!/bin/sh
KNOWLEDGE=docs/knowledge/product.md

# The trap first, and out of the commit the world was made from: this project's
# knowledge held no frame before the sitting. Reading the working copy would
# report the block the sitting just wrote as proof that it was always there.
BEFORE=$(git show main:$KNOWLEDGE 2>/dev/null) || { echo "no knowledge was planted at all"; exit 1; }
case "$BEFORE" in *'**[frame '*) echo "the trap was not planted: a frame stood before the sitting"; exit 1;; esac

# The identifier is asked of the kit rather than read off whatever came out: a
# judge that asserts what it was given is a judge that cannot fail.
ID=$(python3 -c "from agent_kit.knowledge import identifier; print(identifier('an-evening', 'ставка живёт одной константой, своей никто не заводит'))") ||
  { echo "the kit could not say what the identifier must be"; exit 3; }

grep -q "id: $ID" "$KNOWLEDGE" || { echo "no block carries the identifier the kit derives: $ID"; exit 1; }
grep -q '\*\*\[frame ' "$KNOWLEDGE" || { echo "the block was written, and not as a frame"; exit 1; }
grep -q 'ставка живёт одной константой' "$KNOWLEDGE" || { echo "the frame lost its own words"; exit 1; }

# Under the record it addressed, and not at the foot of the file: an address
# nobody resolved is a block that lands wherever the writer guessed.
# `Части` is neither the first record of this file nor the last, so "somewhere
# below it" is not the same sentence as "somewhere in the file".
awk '/^## Части/{seen=1; next} /^## /{seen=0} seen && /\*\*\[frame /{found=1} END{exit !found}' "$KNOWLEDGE" ||
  { echo "the frame did not land under the record it named"; exit 1; }
grep -q '^## Чего мы не делаем' "$KNOWLEDGE" ||
  { echo "the record after the addressed one is gone"; exit 1; }

# And the declaration names the same block, so the evening can close it later.
grep -q "id = \"$ID\"" "$DECLARED" || { echo "the declaration does not name the block that was written"; exit 1; }
exit 0
