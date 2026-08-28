#!/bin/sh
FILE=.agent-kit/v3/manual.md

# The trap first, read out of the commit the world was made from: one line
# really carries both answers, and one really carries neither.
BEFORE=$(git show "main:$FILE" 2>/dev/null) || { echo "no chores were planted at all"; exit 1; }
case "$BEFORE" in *'proof: sh ops/has-key.sh'*'by-hand:'*) ;;
  *) echo "the trap was not planted: no line carries both answers"; exit 1;; esac
case "$BEFORE" in *'`key: bbbbbb`'*'proof'*) echo "the trap was not planted: the naked line has a proof"; exit 1;; esac

# The door ranks the line with both, because it carries a proof.
SAID=$($KIT next) || { echo "the door did not answer"; exit 1; }
case "$(printf '%s\n' "$SAID" | head -1)" in
  manual-due*) ;;
  *) echo "the door does not rank a line that carries a proof"; exit 1 ;;
esac

WALKED=$($KIT manual check) || { echo "the check did not come back"; exit 1; }

# What the door ranked, the walk ran: otherwise it is a rung nothing removes.
printf '%s\n' "$WALKED" | grep -q 'manual-done: aaaaaa' ||
  { echo "the door ranks it and the walk never runs it: $WALKED"; exit 1; }
grep -q 'aaaaaa' "$FILE" && { echo "the proof passed and the line still stands"; exit 1; }

# What the kit cannot close, it does not run and does not erase.
printf '%s\n' "$WALKED" | grep -q 'manual-nobody-can-close: bbbbbb' ||
  { echo "a line with neither answer was not named as one: $WALKED"; exit 1; }
grep -q 'bbbbbb' "$FILE" ||
  { echo "the kit erased what the owner wrote down for themselves"; exit 1; }
exit 0
