#!/bin/sh
LEDGER=docs/knowledge/debt.md
# The trap: the line stood in the checkout and in no commit. If it had been
# committed, the copy in the run's tree would hold it too and this case would
# be measuring nothing at all.
git show "main:$LEDGER" >/dev/null 2>&1 && { echo "the trap was not planted: the ledger was committed"; exit 1; }
git log --all --format=%H -- "$LEDGER" | grep -q . && { echo "the trap was not planted: some commit holds the ledger"; exit 1; }

# The run got past `record` — which is what a night dying on `no-such-debt`
# after four paid steps would not have done — and the evening then took the
# line away, because the work answered it.
test -f "$LEDGER" || { echo "the ledger the owner had is gone entirely"; exit 1; }
grep -q '6kwgcv' "$LEDGER" && { echo "the line the work answered is still standing"; exit 1; }
grep -q '^## Работает плохо' "$LEDGER" || { echo "the section went with the line"; exit 1; }
exit 0
