#!/bin/sh
LEDGER=docs/knowledge/debt.md
# The trap: rates really did name a line — its `record` ran and left it in the
# step's own papers — and its delivery really did refuse afterwards. Without
# both, "its line is not in the ledger" is a sentence about nothing.
SAID=.agent-kit/v3/runs/rates/steps/4-record/output.json
test -f "$SAID" || { echo "rates never recorded anything, so it named no line"; exit 1; }
grep -q 'the table is read twice' "$SAID" || { echo "the trap was not planted: rates named no line"; exit 1; }
grep -q '"status": "failed"' .agent-kit/v3/batches/vat/batch.json ||
  { echo "the trap was not planted: nothing failed"; exit 1; }

test -f "$LEDGER" || { echo "the feature that landed left no ledger at all"; exit 1; }
grep -q 'the quoting rounds before it adds' "$LEDGER" ||
  { echo "the feature that landed did not reach the ledger"; exit 1; }
grep -q 'the table is read twice' "$LEDGER" &&
  { echo "a feature that did not land put its finding in the owner's ledger"; exit 1; }
exit 0
