#!/bin/sh
KNOWLEDGE=docs/knowledge/entities.md

# The trap first, read out of the commit the world was made from rather than
# out of the working copy the run has already edited: the record really is
# keyed in the project's own language, its key really is not its heading, and
# the block was not there before the run.
BEFORE=$(git show main:$KNOWLEDGE 2>/dev/null) || { echo "no knowledge was planted at all"; exit 1; }
case "$BEFORE" in *'`key: налог`'*) : ;; *) echo "the trap was not planted: no key outside ASCII"; exit 1;; esac
case "$BEFORE" in *'### налог'*) echo "the trap was not planted: the key is also a heading"; exit 1;; esac
case "$BEFORE" in *kit/add-vat*) echo "the block was already there before the run"; exit 1;; esac

# The key, and not the heading, is what the driver enclosed as the address.
INPUT="$RUN_DIR/steps/0-design/attempt-1/input.md"
test -s "$INPUT" || { echo "the design step was never given an input to read"; exit 1; }
grep -q 'entities.md#налог' "$INPUT" || { echo "the index does not print the key as the address"; exit 1; }

# And the block landed under the record that key addresses — not merely
# somewhere in the file: the record is neither the first nor the last, so
# "below its heading" is a different sentence from "at the end".
awk '/^### Ставка налога/{seen=1; next} /^### /{seen=0} seen && /kit\/add-vat/{found=1} END{exit !found}' "$KNOWLEDGE" ||
  { echo "the block is not under the record its key addressed"; exit 1; }
grep -q '^### Скидка' "$KNOWLEDGE" || { echo "the record after the addressed one is gone"; exit 1; }

git show --name-only --format= HEAD | grep -q "$KNOWLEDGE" ||
  { echo "the knowledge was written but never committed"; exit 1; }
exit 0
