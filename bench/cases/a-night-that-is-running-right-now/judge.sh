#!/bin/sh
# The trap first: the lease is really in the ledger, really against this
# project, and the run it names really is one the door would otherwise offer to
# start. Read out of the ledger itself, because `machine` reaps before it
# prints and this is a row a reader could kill.
HELD=$(python3 - <<'READ'
import os, sqlite3
where = os.path.join(os.environ["XDG_STATE_HOME"], "agent-kit", "daemon.sqlite")
rows = sqlite3.connect(where).execute(
    "SELECT kind, slug, pid FROM leases WHERE project = ? AND kind = 'run'",
    (os.environ["REPO"],),
).fetchall()
print(";".join(f"{kind}:{slug}:{pid}" for kind, slug, pid in rows))
READ
) || { echo "the ledger could not be read"; exit 1; }
case "$HELD" in
  *run:rates:1*) ;;
  *) echo "the trap was not planted: the ledger holds ${HELD:-nothing}"; exit 1 ;;
esac
grep -q '"status": "created"' "$REPO/.agent-kit/v3/runs/rates/run.json" ||
  { echo "the trap was not planted: the leased run is not one the door would start"; exit 1; }

SAID=$($KIT -C "$REPO" next) || { echo "the door did not answer"; exit 1; }
FIRST=$(printf '%s\n' "$SAID" | head -1)
case "$FIRST" in
  a-night-is-running:*rates*) ;;
  *) echo "the door answered $FIRST rather than a-night-is-running about rates"; exit 1 ;;
esac
# And not printed again below with a command the lease refuses by name. This is
# the half the door was failing: the rung stood, and the same run was offered
# underneath it with `run go`.
printf '%s\n' "$SAID" | grep -q "agent-kit run go rates" &&
  { echo "a run somebody is driving was offered to be started"; exit 1; }
printf '%s\n' "$SAID" | grep -q "run-created" &&
  { echo "a run somebody is driving was named again as one nobody has started"; exit 1; }
exit 0
