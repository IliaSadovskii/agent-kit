#!/bin/sh
KNOWLEDGE=docs/knowledge/entities.md

# The trap first: the fence really is opened and really is never closed, and
# what it swallows is a record and a block — the two things a judge that only
# counted an exit code would never notice were missing.
test -s "$KNOWLEDGE" || { echo "no knowledge was planted at all"; exit 1; }
test "$(grep -c '^```' "$KNOWLEDGE")" = 1 || { echo "the trap was not planted: the fence is not lonely"; exit 1; }
grep -q '^### Налог' "$KNOWLEDGE" || { echo "the trap was not planted: nothing stands below the fence"; exit 1; }
grep -q 'id: k7f3q2' "$KNOWLEDGE" || { echo "the trap was not planted: no block stands below the fence"; exit 1; }

# The refusal names itself by code, and the code is the one for a file that
# cannot be read honestly.
grep -q 'unreadable-knowledge' "$BENCH/kit-said" ||
  { echo "the run was refused, and not for the file: $(tail -1 "$BENCH/kit-said")"; exit 1; }

# Nothing was spent on it: no session was asked anything, and the knowledge is
# untouched.
test ! -d "$RUN_DIR/steps" || { echo "a session was paid for against a file the kit cannot read"; exit 1; }
if grep -q 'kit/add-vat' "$KNOWLEDGE"; then echo "a block was written into a file the kit cannot read"; exit 1; fi
exit 0
