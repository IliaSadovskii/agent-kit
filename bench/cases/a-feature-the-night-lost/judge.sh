#!/bin/sh
# The trap first: the feature really failed, and the trace the door leans on —
# the tree of a run that did not land — is really standing.
grep -q '"status": "failed"' "$BATCH_FILE" ||
  { echo "the trap was not planted: no feature failed"; exit 1; }
test -d "$TREES/add-vat" ||
  { echo "the trap was not planted: the failed feature left no tree"; exit 1; }

SAID=$($KIT -C "$REPO" next) || { echo "the door did not answer"; exit 1; }
FIRST=$(printf '%s\n' "$SAID" | head -1)
case "$FIRST" in
  run-failed:*) ;;
  *) echo "the door answered ${FIRST%%:*} rather than run-failed"; exit 1 ;;
esac
# The batch owns the name and not the rank: both words, on the answer's line.
case "$FIRST" in
  *vat/add-vat*) ;;
  *) echo "the answer names $FIRST, not the batch beside the feature"; exit 1 ;;
esac
printf '%s\n' "$SAID" | grep -q "nothing-is-due" &&
  { echo "a night that lost its feature was called quiet"; exit 1; }
exit 0
