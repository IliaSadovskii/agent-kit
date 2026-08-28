#!/bin/sh
FILE=.agent-kit/v3/manual.md

# The trap first: both features really named a chore, and there was no such
# file before the night. A judge that reads only the result is green in a world
# where nobody named anything.
for FEATURE in rates quote; do
  DESIGN=.agent-kit/v3/runs/$FEATURE/steps/0-design/output.json
  test -f "$DESIGN" || { echo "$FEATURE never designed anything"; exit 1; }
  grep -q 'STRIPE_KEY' "$DESIGN" ||
    { echo "the trap was not planted: $FEATURE named no chore"; exit 1; }
done
git show "main:$FILE" >/dev/null 2>&1 &&
  { echo "the trap was not planted: the file stood before the night"; exit 1; }

test -f "$FILE" || { echo "the chore reached no file at all"; exit 1; }

# The keys are asked of the kit rather than read off whatever came out.
KEY=$(python3 -c "from agent_kit.manual import manual_key; print(manual_key('положить STRIPE_KEY в окружение продакшена'))") ||
  { echo "the kit could not say what the key must be"; exit 3; }
grep -q "key: $KEY" "$FILE" || { echo "no line carries the key the kit derives: $KEY"; exit 1; }
grep -q 'proof: sh ops/has-key.sh' "$FILE" || { echo "the line lost the command that closes it"; exit 1; }
grep -q 'применить миграцию 0007' "$FILE" || { echo "the second feature's chore reached nobody"; exit 1; }

# One line for what two features both need placed, and no more — in the file,
# and in the evening's own memory of what it laid. The file alone does not
# measure it: writing a key that already stands replaces the line, so a night
# with no memory would leave one line and two entries, name it twice to the
# owner, and lay it again the night after somebody did the work.
test "$(grep -c 'STRIPE_KEY' "$FILE")" = 1 ||
  { echo "two features that need one key placed got two lines"; exit 1; }
test "$(grep -c "\"key\": \"$KEY\"" "$BATCH_FILE")" = 1 ||
  { echo "the evening remembers laying one chore twice"; exit 1; }
test "$(grep -c '^- ' "$FILE")" = 2 ||
  { echo "the file holds $(grep -c '^- ' "$FILE") lines and the night named two"; exit 1; }

# It survives this machine: repository content, in the owner's checkout, and
# committed by nobody — the owner reads the diff, as after a sitting.
git check-ignore -q "$FILE" &&
  { echo "the file is ignored, so the chore dies with this machine"; exit 1; }
test -n "$(git status --porcelain -- "$FILE")" || { echo "the kit committed it itself"; exit 1; }
git show --name-only --format= kit/rates | grep -q "$FILE" &&
  { echo "the chore rode a feature's branch"; exit 1; }
exit 0
