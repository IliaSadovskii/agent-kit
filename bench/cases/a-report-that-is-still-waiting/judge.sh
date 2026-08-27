#!/bin/sh
# The trap first: the delivered run is really there, really done, and its work
# really is not in the trunk yet.
grep -q '"status": "done"' "$REPO/.agent-kit/v3/runs/old-work/run.json" ||
  { echo "the trap was not planted: no delivered run stands"; exit 1; }
test -n "$(git -C "$REPO" cherry main kit/old-work | grep '^+')" ||
  { echo "the trap was not planted: the branch is already in the trunk"; exit 1; }

SAID=$($KIT -C "$REPO" next) || { echo "the door did not answer"; exit 1; }
printf '%s\n' "$SAID" | grep -q "pull-request-waiting.*old-work" ||
  { echo "the door did not name the report that is waiting"; exit 1; }
printf '%s\n' "$SAID" | grep -q "pull/11" ||
  { echo "the door did not name where the owner reads it"; exit 1; }
exit 0
