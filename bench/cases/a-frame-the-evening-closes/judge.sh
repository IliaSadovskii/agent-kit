#!/bin/sh
KNOWLEDGE=docs/knowledge/product.md

# The trap first, out of the commit the world was made from: a real frame block,
# with a real identifier, standing before the night ran. Reading the working copy
# would report a block the night deleted as one that was never planted, which is
# the judge lying about itself.
BEFORE=$(git show main:$KNOWLEDGE 2>/dev/null) || { echo "no knowledge was planted at all"; exit 1; }
case "$BEFORE" in *'id: fr4me1'*) : ;; *) echo "the trap was not planted: no block with that identifier"; exit 1;; esac
case "$BEFORE" in *'**[frame '*) : ;; *) echo "the trap was not planted: the block is not a frame"; exit 1;; esac

# And the night really did end: a batch with anything left to build keeps its
# frames standing, so a case where nothing ran would pass a check on the file
# alone for the wrong reason.
grep -q '"status": "done"' "$BATCH_FILE" || { echo "the feature never landed, so nothing was over"; exit 1; }

grep -q 'id: fr4me1' "$KNOWLEDGE" && { echo "the frame is still standing after the night ended"; exit 1; }
# What it stood under is untouched, and so is what came after it.
grep -q '^### Налог' "$KNOWLEDGE" || { echo "closing took the record it stood under with it"; exit 1; }
grep -q '^### Скидка' "$KNOWLEDGE" || { echo "closing took the record after it as well"; exit 1; }
grep -q 'key: money' "$KNOWLEDGE" || { echo "closing took the parts of the product"; exit 1; }

# The batch no longer claims to hold a block it has deleted.
grep -q '"id": "fr4me1"' "$BATCH_FILE" && { echo "the batch still names a block that is gone"; exit 1; }
exit 0
