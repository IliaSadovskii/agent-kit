#!/bin/sh
FILE=.agent-kit/v3/manual.md

# The trap first: the design really named a chore no command can prove, and no
# such file stood before the night.
DESIGN=.agent-kit/v3/runs/rates/steps/0-design/output.json
grep -q 'by_hand' "$DESIGN" 2>/dev/null ||
  { echo "the trap was not planted: nothing needed a person"; exit 1; }
git show "main:$FILE" >/dev/null 2>&1 &&
  { echo "the trap was not planted: the file stood before the night"; exit 1; }

KEY=$(python3 -c "from agent_kit.manual import manual_key; print(manual_key('подтвердить домен кодом из SMS'))") ||
  { echo "the kit could not say what the key must be"; exit 3; }

# It stands, and it says in its own words why nothing can prove it.
test -f "$FILE" || { echo "the chore reached no file at all"; exit 1; }
grep -q "key: $KEY" "$FILE" || { echo "no line carries the key the kit derives: $KEY"; exit 1; }
grep -q 'by-hand: код приходит на телефон владельца' "$FILE" ||
  { echo "the line does not say why no command can prove it"; exit 1; }
# On a line, not in the header: the header says what `proof:` means.
grep -q '^- .*proof:' "$FILE" && { echo "a chore nobody can prove was given a command"; exit 1; }

# The check names it and runs nothing for it.
SAID=$($KIT manual check) || { echo "the check did not come back"; exit 1; }
printf '%s\n' "$SAID" | grep -q "manual-by-hand: $KEY" ||
  { echo "the check did not name the chore only a person can close: $SAID"; exit 1; }
grep -q "key: $KEY" "$FILE" || { echo "the check took away a line it can never prove"; exit 1; }

# And it puts the door on no rung: a rung nothing can remove is a rung the door
# stops descending at, which is what `run-failed` was fixed for.
DOOR=$($KIT next) || { echo "the door did not answer"; exit 1; }
case "$(printf '%s\n' "$DOOR" | head -1)" in
  manual-due*) echo "the door stands on a chore it can never take away"; exit 1 ;;
esac
printf '%s\n' "$DOOR" | grep -q "$KEY" ||
  { echo "the chore is ranked nowhere and printed nowhere either"; exit 1; }
exit 0
