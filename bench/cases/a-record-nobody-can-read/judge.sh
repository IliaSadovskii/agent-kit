#!/bin/sh
# The trap first: the damaged record is really there and really damaged.
test -s "$REPO/.agent-kit/v3/runs/last-summer/run.json" ||
  { echo "the trap was not planted: no record was left to break"; exit 1; }
python3 -c "import json,sys; json.load(open(sys.argv[1]))" \
  "$REPO/.agent-kit/v3/runs/last-summer/run.json" 2>/dev/null &&
  { echo "the trap was not planted: the record parses"; exit 1; }

SAID=$($KIT -C "$REPO" next) || { echo "the door did not answer"; exit 1; }
printf '%s\n' "$SAID" | grep -q "unreadable-run" ||
  { echo "the door said nothing about a record it could not read"; exit 1; }
printf '%s\n' "$SAID" | grep -q "last-summer" ||
  { echo "the door did not name which record it could not read"; exit 1; }
# And the whole point: the broken one hid nothing. Which rung answered is not
# asked — that would be this judge reading somebody else's mechanism. What is
# asked is that the pass got past the damage: an answer of its own, and the
# view built after it.
FIRST=$(printf '%s\n' "$SAID" | head -1)
case "$FIRST" in
  unreadable*) echo "a record nobody can read became the whole answer"; exit 1 ;;
esac
printf '%s\n' "$SAID" | grep -q "where this project stands" ||
  { echo "one unreadable record stopped the door before it read anything else"; exit 1; }
exit 0
