#!/bin/sh
QUIET="$BENCH/quiet"
# The trap first: the quiet project is a whole one, it has no runs, and the
# chore standing in it is one the kit could take away.
test -f "$QUIET/.agent-kit/v3/project.toml" ||
  { echo "the trap was not planted: no second project was built"; exit 1; }
test ! -d "$QUIET/.agent-kit/v3/runs" ||
  { echo "the trap was not planted: the quiet project has runs"; exit 1; }
grep -q 'proof: touch ran-here' "$QUIET/.agent-kit/v3/manual.md" ||
  { echo "the trap was not planted: no chore with a proof stands there"; exit 1; }
# The proof leaves a mark if anybody runs it, so *nobody ran it* is a claim this
# judge can fail rather than a file that never existed in this world.
test ! -f "$QUIET/ran-here" || { echo "the trap was not planted: something ran the proof first"; exit 1; }

SAID=$($KIT -C "$QUIET" next) || { echo "the door did not answer"; exit 1; }
FIRST=$(printf '%s\n' "$SAID" | head -1)
case "$FIRST" in
  manual-due*) ;;
  *) echo "the door answered ${FIRST%%:*} in a project that owes a person work"; exit 1 ;;
esac
printf '%s\n' "$SAID" | grep -q "agent-kit manual check" ||
  { echo "the door named no way to find out what is already done"; exit 1; }

# A door that acts is not a door: the proof is run by the command it names,
# and running it here would leave the mark the trap has just shown is absent.
test ! -f "$QUIET/ran-here" || { echo "the door ran the proof itself"; exit 1; }
$KIT -C "$QUIET" manual check >/dev/null || { echo "the check did not come back"; exit 1; }
test -f "$QUIET/ran-here" || { echo "the command the door names runs nothing either"; exit 1; }
exit 0
