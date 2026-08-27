#!/bin/sh
PRODUCT=docs/knowledge/product.md
ROOM=$(ls -d .agent-kit/v3/sittings/*/ | head -1)

# The trap first: what was written down really did say the other thing, and the
# wording this run settles on was not there before it. The baseline is described
# now, so the file existing proves nothing — the two greps below are what do.
BEFORE=$(git show main:$PRODUCT 2>/dev/null) || { echo "the trap was not planted: no description at all"; exit 1; }
case "$BEFORE" in *"сумма и ставка"*) : ;; *) echo "the trap was not planted: nothing to contradict"; exit 1;; esac
case "$BEFORE" in *"и валюта"*) echo "the settled wording was there before the run"; exit 1;; esac
grep -q '"contradicts"' "$ROOM/steps/0-reading/output.json" ||
  { echo "the trap was not planted: the reading contradicted nothing"; exit 1; }

# The question was put, and exactly one was.
test "$(grep -c '^? ' "$BENCH/kit-said")" -eq 1 ||
  { echo "$(grep -c '^? ' "$BENCH/kit-said") questions were put, and the reading had one"; exit 1; }
grep -q 'запись устарела' "$ROOM/answers.txt" || { echo "the answer was not kept"; exit 1; }

# The answer reached the second turn as something to read.
grep -q 'запись устарела' "$ROOM/steps/1-settling/attempt-1/input.md" ||
  { echo "the settling turn was never shown what the owner said"; exit 1; }

# The round is one. A third reply is scripted and must never be reached.
test ! -d "$ROOM/steps/2-settling" && test ! -d "$ROOM/steps/1-settling/attempt-2" ||
  { echo "a second round was opened, and a round is one"; exit 1; }

# And what is on file is what the answer settled, not what the reading asked.
# The settled wording, and not the one the reading asked about: what separates
# them is `settle`, which is this case's own mechanism. That one line per key is
# left standing afterwards belongs to `the-same-telling-told-twice`, and
# asserting it here would make two cases redden for one break.
grep -q 'сумма, ставка и валюта, из которых считается цена' $PRODUCT ||
  { echo "the settled wording is not what was written"; exit 1; }
# Inert as `$`: a part's line always ends in its mark. What tells the reading's
# wording from the answer's is the words after it.
grep -q 'сумма, ставка и валюта —' $PRODUCT &&
  { echo "what the reading asked about was written instead of what the answer settled"; exit 1; }
exit 0
