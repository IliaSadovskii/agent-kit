#!/bin/sh
KNOWLEDGE=docs/knowledge/stack.md

# The trap first, read out of the commit the world was made from: the headings
# really are spaced by hand — one with two spaces, one with a tab — and the
# block was not there before the run.
BEFORE=$(git show main:$KNOWLEDGE 2>/dev/null) || { echo "no knowledge was planted at all"; exit 1; }
printf '%s\n' "$BEFORE" | grep -q '^##  Чем меряем$' ||
  { echo "the trap was not planted: no heading with two spaces"; exit 1; }
printf '%s\n' "$BEFORE" | awk '/^##\tЧем платим$/{found=1} END{exit !found}' ||
  { echo "the trap was not planted: no heading with a tab"; exit 1; }
case "$BEFORE" in *kit/add-vat*) echo "the block was already there before the run"; exit 1;; esac

# Both are addresses, and both are printed the way the program reads them back:
# an anchor that kept its space is an address the index prints and `resolve`
# refuses, which is the thing this case is about.
INPUT="$RUN_DIR/steps/0-design/attempt-1/input.md"
test -s "$INPUT" || { echo "the design step was never given an input to read"; exit 1; }
grep -q 'stack.md#Чем меряем' "$INPUT" || { echo "the two-spaced heading is not an address in the index"; exit 1; }
grep -q 'stack.md#Чем платим' "$INPUT" || { echo "the tabbed heading is not an address in the index"; exit 1; }
grep -q 'stack.md# ' "$INPUT" && { echo "the index prints an address carrying the spacing"; exit 1; }

# And the block landed under the heading it addressed, which is neither the
# first of the file nor the last.
awk '/^##\tЧем платим/{seen=1; next} /^## /{seen=0} seen && /kit\/add-vat/{found=1} END{exit !found}' "$KNOWLEDGE" ||
  { echo "the block is not under the heading it addressed"; exit 1; }
grep -q '^## Как зовём модель' "$KNOWLEDGE" || { echo "the heading after the addressed one is gone"; exit 1; }
exit 0
