#!/bin/sh
# The trap first: the session really did name an hour, and named it in prose.
grep -q 'provider-limited' "$RUN_DIR/run.json" || { echo "no session ever said it was limited"; exit 1; }

$KIT machine > "$BENCH/after" 2>&1 || { echo "the machine could not be read"; exit 3; }
grep -q 'guessed' "$BENCH/after" ||
  { echo "a phrase nobody could read was passed off as an hour that was read"; exit 1; }
grep -q '5pm (America/Los_Angeles)' "$BENCH/after" ||
  { echo "the guess does not say what it was guessed from"; exit 1; }

# And the hour it stands until is a real one, within a day of now. Stored as it
# came, "5pm …" sorts above every date there will ever be: the account would be
# limited for good, and no sweep would ever clear it.
# Asked of the ledger and not scraped off the screen: `until (\S+)` was reading
# an English word out of `agent-kit machine`, and it went red on the translation
# with the mechanism untouched. The hour is a value the kit stores and hands
# back, which is what a case is allowed to measure.
$PYTHON - <<'PY' || exit 1
import datetime, sys
from agent_kit.machine import Ledger, ledger_path
from agent_kit.paths import Paths

limits = Ledger(ledger_path(Paths.from_env())).picture().limits
if not limits:
    print("the limit says no hour at all"); sys.exit(1)
until = datetime.datetime.fromisoformat(limits[0].until)
if until > datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1):
    print(f"the account is limited until {until}, which is not an hour anybody said"); sys.exit(1)
PY
exit 0
