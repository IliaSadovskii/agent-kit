#!/bin/sh
# The trap first: the batch is really there, really unfinished, and the feature
# it owns really has a run standing at `created`.
grep -q '"name": "vat"' "$REPO/.agent-kit/v3/batches/vat/batch.json" ||
  { echo "the trap was not planted: no batch was created"; exit 1; }
grep -q '"status": "created"' "$REPO/.agent-kit/v3/runs/rates/run.json" ||
  { echo "the trap was not planted: the owned feature has no run waiting"; exit 1; }

SAID=$($KIT -C "$REPO" next) || { echo "the door did not answer"; exit 1; }
FIRST=$(printf '%s\n' "$SAID" | head -1)
case "$FIRST" in
  batch-unfinished:*vat*) ;;
  *) echo "the door answered $FIRST rather than batch-unfinished about vat"; exit 1 ;;
esac
printf '%s\n' "$SAID" | grep -q "run-created" &&
  { echo "a feature its batch will start was named as a run to start by hand"; exit 1; }
# Nothing here asks what the door says about the run that landed. That is
# another mechanism, and a judge that reddens for a neighbour's break cannot
# say what it measures — `a-feature-the-night-lost` is where the batch's name
# beside a feature's is judged, on the rung that case is about.
exit 0
