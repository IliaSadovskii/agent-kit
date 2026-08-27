#!/bin/sh
QUIET="$BENCH/quiet"
# The trap first: the quiet project is really a whole one — declared, described,
# with something to check itself with — and really has no runs.
test -f "$QUIET/.agent-kit/v3/project.toml" ||
  { echo "the trap was not planted: no second project was built"; exit 1; }
test -f "$QUIET/docs/knowledge/product.md" ||
  { echo "the trap was not planted: the second project describes nothing"; exit 1; }
test ! -d "$QUIET/.agent-kit/v3/runs" ||
  { echo "the trap was not planted: the quiet project has runs"; exit 1; }

SAID=$($KIT -C "$QUIET" next) || { echo "the door did not answer"; exit 1; }
FIRST=$(printf '%s\n' "$SAID" | head -1)
case "$FIRST" in
  nothing-is-due*) ;;
  *) echo "the door answered ${FIRST%%:*} in a project with nothing in it"; exit 1 ;;
esac
printf '%s\n' "$SAID" | grep -q "batch compose" ||
  { echo "the door named no way to decide what is next"; exit 1; }
exit 0
