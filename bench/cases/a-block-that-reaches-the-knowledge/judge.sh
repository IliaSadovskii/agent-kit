#!/bin/sh
KNOWLEDGE=docs/knowledge/entities.md

# The trap first, read out of the commit the world was made from rather than out
# of the working copy the run has already edited: a judge that reads only the
# result is green in a project where nobody planted anything.
BEFORE=$(git show main:$KNOWLEDGE 2>/dev/null) || { echo "no knowledge was planted at all"; exit 1; }
test -n "$BEFORE" || { echo "the planted knowledge is empty"; exit 1; }
case "$BEFORE" in *kit/add-vat*) echo "the block was already there before the run"; exit 1;; esac
case "$BEFORE" in *"id: k7f3q2"*) : ;; *) echo "the block this run closes was never planted"; exit 1;; esac
case "$BEFORE" in *"### Скидка"*) : ;; *) echo "the addressed record is the last one, so its end is the file's"; exit 1;; esac

test -s "$KNOWLEDGE" || { echo "the knowledge is gone"; exit 1; }
grep -q 'kit/add-vat' "$KNOWLEDGE" || { echo "the run wrote no block into the knowledge"; exit 1; }

# Under the record it addressed — `tax` — which is neither the first record nor
# the last. "Somewhere below `### Налог`" is the end of the file as well, and a
# judge that says only that is green against a writer that appends blindly.
awk '/^### Налог/{seen=1; next} /^### /{seen=0} seen && /kit\/add-vat/{found=1} END{exit !found}' "$KNOWLEDGE" ||
  { echo "the block is not under the record it addressed"; exit 1; }
grep -q '^### Скидка' "$KNOWLEDGE" || { echo "the record after the addressed one is gone"; exit 1; }

# The identifier is derived, not drawn: the kit can say what it must be.
WANT=$(python3 -c "from agent_kit.knowledge import identifier; print(identifier('add-vat', 'the rate is a whole percent'))") ||
  { echo "the kit could not say what the identifier should be"; exit 3; }
grep -q "id: $WANT\]" "$KNOWLEDGE" || { echo "the block carries an identifier this run would not produce again"; exit 1; }

# What it closed is gone, and only that.
if grep -q 'id: k7f3q2' "$KNOWLEDGE"; then echo "the block the design closed is still there"; exit 1; fi
grep -q '^### Деньги' "$KNOWLEDGE" || { echo "closing took the record with it"; exit 1; }

# And it reached the commit, not only the disk.
git show --name-only --format= HEAD | grep -q "$KNOWLEDGE" ||
  { echo "the knowledge was written but never committed"; exit 1; }
git show --name-only --format= HEAD | grep -q 'money.py' ||
  { echo "the code the build named is not in the commit"; exit 1; }
exit 0
