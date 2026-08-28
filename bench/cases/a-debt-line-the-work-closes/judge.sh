#!/bin/sh
LEDGER=docs/knowledge/debt.md
# Both lines really stood before the night, read out of the commit the world was
# made from: "the line is gone" is green in a world where it was never there.
BEFORE=$(git show "main:$LEDGER" 2>/dev/null) || { echo "no ledger was planted at all"; exit 1; }
case "$BEFORE" in *6kwgcv*) ;; *) echo "the line the work answers was not planted"; exit 1;; esac
case "$BEFORE" in *g6mgmm*) ;; *) echo "the neighbour that must survive was not planted"; exit 1;; esac

grep -q '6kwgcv' "$LEDGER" && { echo "the line the work answered is still standing"; exit 1; }
grep -q 'g6mgmm' "$LEDGER" || { echo "closing one line took its neighbour with it"; exit 1; }
grep -q '^## Работает плохо' "$LEDGER" || { echo "the section went with the line"; exit 1; }
test -n "$(git status --porcelain -- "$LEDGER")" || { echo "the kit committed the removal itself"; exit 1; }
exit 0
