#!/bin/sh
FILE=.agent-kit/v3/manual.md

# The trap first, read out of the commit the world was made from: both lines
# really stood, and one of them really was already done. "The line is gone" is
# green in a world where it was never there.
BEFORE=$(git show "main:$FILE" 2>/dev/null) || { echo "no chores were planted at all"; exit 1; }
case "$BEFORE" in *aaaaaa*) ;; *) echo "the line that is done was not planted"; exit 1;; esac
case "$BEFORE" in *bbbbbb*) ;; *) echo "the line that must survive was not planted"; exit 1;; esac

SAID=$($KIT manual check) || { echo "the check did not come back"; exit 1; }
printf '%s\n' "$SAID" | grep -q 'manual-done: aaaaaa' ||
  { echo "the proof that passed was not said to have closed anything: $SAID"; exit 1; }
printf '%s\n' "$SAID" | grep -q 'manual-stands: bbbbbb' ||
  { echo "the proof that failed did not leave its line standing: $SAID"; exit 1; }

grep -q 'aaaaaa' "$FILE" && { echo "the proof passed and its line still stands"; exit 1; }
grep -q 'bbbbbb' "$FILE" || { echo "closing one line took the other with it"; exit 1; }
grep -q '^# Сделать руками' "$FILE" || { echo "the header went with the line"; exit 1; }

# The kit does not commit: the owner deletes it in the commit that does the work.
test -n "$(git status --porcelain -- "$FILE")" || { echo "the kit committed the removal itself"; exit 1; }
exit 0
