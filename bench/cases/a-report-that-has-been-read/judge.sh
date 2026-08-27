#!/bin/sh
# The trap first: there really is a delivered run with a pull request recorded,
# and its work really is in the trunk under a different commit — which is what
# a squash makes and what `merge-base --is-ancestor` cannot see.
grep -q 'pull/11' "$REPO/.agent-kit/v3/runs/old-work/steps/1-deliver/output.json" ||
  { echo "the trap was not planted: no pull request was recorded"; exit 1; }
COMMIT=$(sed -n 's/.*"commit": "\([0-9a-f]*\)".*/\1/p' \
  "$REPO/.agent-kit/v3/runs/old-work/steps/1-deliver/output.json")
git -C "$REPO" merge-base --is-ancestor "$COMMIT" main &&
  { echo "the trap was not planted: the commit is an ancestor, so nothing is being measured"; exit 1; }
test -z "$(git -C "$REPO" cherry main kit/old-work | grep '^+')" ||
  { echo "the trap was not planted: the work is not in the trunk"; exit 1; }

SAID=$($KIT -C "$REPO" next) || { echo "the door did not answer"; exit 1; }
# One line that says the rung is alive at all. A judge that only ever says
# *not this one* is green when the rung has died altogether, which is the same
# green it gives when the rung works.
printf '%s\n' "$SAID" | grep -q "pull-request-waiting.*add-vat" ||
  { echo "the rung is not naming anything, so nothing was measured about old-work"; exit 1; }
printf '%s\n' "$SAID" | grep -q "pull-request-waiting.*old-work" &&
  { echo "the door still names a report whose work is already in the trunk"; exit 1; }
exit 0
