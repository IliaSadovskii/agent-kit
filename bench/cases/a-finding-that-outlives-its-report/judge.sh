#!/bin/sh
LEDGER=docs/knowledge/debt.md

# The trap first: the finding was really planted, and there was no ledger to
# find it in. A judge that reads only the result is green in a world where the
# review found nothing at all.
REVIEW=.agent-kit/v3/runs/rates/steps/3-review/output.json
test -f "$REVIEW" || { echo "the feature never reviewed anything"; exit 1; }
grep -q 'worth-fixing' "$REVIEW" || { echo "the trap was not planted: the review found nothing"; exit 1; }
git show "main:$LEDGER" >/dev/null 2>&1 && { echo "the trap was not planted: a ledger stood before the night"; exit 1; }

# The key is asked of the kit rather than read off whatever came out.
KEY=$(python3 -c "from agent_kit.knowledge import debt_key; print(debt_key('the retry loop swallows the reason it failed'))") ||
  { echo "the kit could not say what the key must be"; exit 3; }

test -f "$LEDGER" || { echo "the finding reached no ledger at all"; exit 1; }
grep -q "key: $KEY" "$LEDGER" || { echo "no line carries the key the kit derives: $KEY"; exit 1; }
grep -q 'the retry loop swallows the reason it failed' "$LEDGER" || { echo "the line lost its own words"; exit 1; }
grep -q 'run: rates' "$LEDGER" || { echo "the line does not say which night found it"; exit 1; }
grep -q 'the name could be shorter' "$LEDGER" && { echo "a note became debt: it blocks nothing and costs nothing"; exit 1; }

# Under the heading its kind names, and not at the foot of the file.
awk '/^## Работает плохо/{seen=1; next} /^## /{seen=0} seen && /the retry loop swallows/{found=1} END{exit !found}' "$LEDGER" ||
  { echo "the line did not land under the section its kind names"; exit 1; }

# The kit does not commit: the owner reads the diff. So the line is in the
# checkout and in no commit of the feature's branch.
test -n "$(git status --porcelain -- "$LEDGER")" || { echo "the ledger was committed by the kit"; exit 1; }
git show --name-only --format= kit/rates | grep -q "$LEDGER" && { echo "the line rode the feature's branch"; exit 1; }
exit 0
