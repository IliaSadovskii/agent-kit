#!/bin/sh
PRODUCT=docs/knowledge/product.md
SIGN_IN=$(python3 -c "from agent_kit.knowledge import part_key; print(part_key('вход'))") ||
  { echo "the kit could not say what the key must be"; exit 3; }
NEWS=$(python3 -c "from agent_kit.knowledge import part_key; print(part_key('уведомления'))")

# The trap first: the repository this ran in really had no description.
git show main:$PRODUCT >/dev/null 2>&1 &&
  { echo "the trap was not planted: a description was there before the sitting"; exit 1; }
grep -q 'knowledge = ""' .agent-kit/v3/project.toml &&
  { echo "the trap was not planted: this project says it keeps none"; exit 1; }

test -s $PRODUCT || { echo "one sitting left no description"; exit 1; }
grep -q "key: $SIGN_IN" $PRODUCT || { echo "the part the owner told is not there"; exit 1; }
grep -q "key: $NEWS" $PRODUCT || { echo "the second part is not there"; exit 1; }

# The mark is today's, counted forward rather than written into the case: a date
# in a fixture is green until that day and red after it.
TODAY=$(date +%F)
grep -q "\`key: $SIGN_IN\` · \`walked: $TODAY\`" $PRODUCT ||
  { echo "the part carries no mark of the day it was walked"; exit 1; }

# On a project with nothing written down there is nothing to contradict, so
# nothing was put to the owner and no second turn was spent.
grep -q 'Google, Apple и почта' $PRODUCT || { echo "what was told is not what is on file"; exit 1; }
test ! -e .agent-kit/v3/sittings/*/answers.txt ||
  { echo "somebody was asked a question in a project with nothing to contradict"; exit 1; }
test ! -d .agent-kit/v3/sittings/*/steps/1-settling ||
  { echo "a settling turn was spent with nothing to settle"; exit 1; }

# What the owner said is kept, whole, beside the description it became.
diff -q "$TELLING" .agent-kit/v3/sittings/*/telling.txt >/dev/null ||
  { echo "the telling on file is not what the owner said"; exit 1; }

# The ledger took what was not about what the product must do, and the ledger's
# lines are not parts: a bug written down does not become a part of the product.
grep -q 'импорт словаря' docs/knowledge/debt.md || { echo "the ledger line went nowhere"; exit 1; }
COUNTED=$(python3 -c "
from agent_kit.knowledge import Knowledge
print(len(Knowledge('docs/knowledge').parts()))
") || { echo "the parts could not be read back"; exit 1; }
test "$COUNTED" -eq 2 || { echo "the description holds $COUNTED parts and the sitting wrote 2"; exit 1; }

# And it is a description a real design step is shown — a run, a session, and
# the input that session was actually handed. Asking `step input` would have
# measured the command that composes one, not the driver that runs one.
cat > "$BENCH/design-reply.json" <<'JSON'
{
  "title": "Money learns a VAT rate",
  "summary": "Money learns a VAT rate.",
  "changes": ["money.py — a RATE beside the amount"],
  "seams": ["AMOUNT keeps its meaning"],
  "asks": [],
  "closes": [],
  "assumptions": []
}
JSON
$KIT -C "$REPO" run new reads-it --brief "что-нибудь" --steps design >/dev/null ||
  { echo "a run could not be created against the described project"; exit 3; }
$KIT -C "$REPO" run go reads-it --provider fake --option "reply=$BENCH/design-reply.json" >/dev/null 2>&1 ||
  { echo "the run was refused against a project the sitting just described"; exit 1; }
SHOWN=.agent-kit/v3/runs/reads-it/steps/0-design/attempt-1/input.md
test -s "$SHOWN" || { echo "the design step was never handed an input"; exit 1; }
grep -q "key: $SIGN_IN" "$SHOWN" ||
  { echo "the session was not shown the description the sitting wrote"; exit 1; }
grep -q "the parts of the product" "$SHOWN" ||
  { echo "the parts reached the session as something other than parts"; exit 1; }
exit 0
