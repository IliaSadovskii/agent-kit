#!/bin/sh
FILE=.agent-kit/v3/manual.md

# The trap first: the line that cannot fail really stood, and beside it one
# that really can — without the second, "nothing was closed" proves nothing.
BEFORE=$(git show "main:$FILE" 2>/dev/null) || { echo "no chores were planted at all"; exit 1; }
case "$BEFORE" in *'proof: true'*) ;; *) echo "the trap was not planted: no proof that cannot fail"; exit 1;; esac
case "$BEFORE" in *bbbbbb*) ;; *) echo "the trap was not planted: nothing here could be closed at all"; exit 1;; esac

SAID=$($KIT manual check) || { echo "the check did not come back"; exit 1; }
printf '%s\n' "$SAID" | grep -q 'manual-proves-nothing: aaaaaa' ||
  { echo "a command that cannot fail was not named as one: $SAID"; exit 1; }
grep -q 'aaaaaa' "$FILE" || { echo "a command that cannot fail closed its own line"; exit 1; }
grep -q 'bbbbbb' "$FILE" && { echo "the honest proof beside it was never run"; exit 1; }
exit 0
