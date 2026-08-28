#!/bin/sh
KNOWLEDGE=docs/knowledge/entities.md

# The trap first, and in three parts. The design really did excuse a kind; the
# review really did name a file the commands were measured over; and there
# really was something for `record` to write — without an expensive assumption
# carrying an address, "the knowledge is untouched" is green in a world where
# nothing was ever going to be written into it.
STEP="$RUN_DIR/steps/0-design"
grep -q 'только прозу' "$STEP/attempt-1/raw.txt" ||
  { echo "the trap was not planted: the design excused nothing"; exit 1; }
grep -q '"expensive": true' "$STEP/attempt-1/raw.txt" ||
  { echo "the trap was not planted: nothing was due to the knowledge"; exit 1; }
grep -q ' money.py"' "$RUN_DIR/steps/2-verify/output.json" ||
  { echo "the trap was not planted: money.py was never measured"; exit 1; }
BEFORE=$(git show main:$KNOWLEDGE 2>/dev/null) || { echo "no knowledge was planted at all"; exit 1; }
test -n "$BEFORE" || { echo "the planted knowledge is empty"; exit 1; }

# The review did its work: it recorded the truth, so the step passed. The run
# stops on what it recorded, under its own code — *a defect was found* and *a
# kind of test was being skipped* are different events for the owner.
grep -q 'why-the-diff-contradicts: types' "$RUN_DIR/run.json" ||
  { echo "the contradiction did not stop the run: $(tail -1 "$BENCH/kit-said")"; exit 1; }
grep -q 'blocked-by-review' "$RUN_DIR/run.json" &&
  { echo "it was folded into the code for an ordinary blocking finding"; exit 1; }

# And it was `record` that asked, before the owner's knowledge was touched.
# It was `record` and not `deliver`: the step in front of the knowledge is the
# one that asked, which is the whole reason the question moved there in S6.
test -d "$RUN_DIR/steps/4-record" || { echo "record was never reached"; exit 1; }
test ! -d "$RUN_DIR/steps/5-deliver" ||
  { echo "the question was asked by deliver, so record let it past the knowledge"; exit 1; }
grep -q 'kit/add-vat' "$KNOWLEDGE" &&
  { echo "a block reached the knowledge although the run refused"; exit 1; }
test "$(git status --porcelain -- "$KNOWLEDGE")" = "" ||
  { echo "the run edited the knowledge before it refused"; exit 1; }

# Nothing reached the owner either: no branch, no pull request.
git rev-parse --verify --quiet "$BRANCH" >/dev/null &&
  { echo "contradicted work was branched anyway"; exit 1; }
test -z "$(find "$BENCH" -maxdepth 1 -name "gh-opened-*" -print -quit)" ||
  { echo "a pull request was opened for contradicted work"; exit 1; }
exit 0
