#!/bin/sh
# The trap first: a slot was actually held when the run started asking.
test -s "$BENCH/planted-at" || { echo "nothing was planted, so nothing was waited for"; exit 1; }
PLANTED=$(cat "$BENCH/planted-at")

# It waited. Without this the case is green against a kit that ignores the
# ceiling entirely, which is the other half of what it must catch.
STARTED=$(python3 - <<'PY' || exit 3
import datetime, json, os
run = json.load(open(os.path.join(os.environ["RUN_DIR"], "run.json")))
first = [step for step in run["steps"] if step["name"] == "design"][0]
print(int(datetime.datetime.fromisoformat(first["started_at"]).timestamp()))
PY
)
test "$((STARTED - PLANTED))" -ge 2 ||
  { echo "the first session started $((STARTED - PLANTED))s after the slot was taken, so it never waited"; exit 1; }

# And it took the slot when it came free rather than giving up on it.
test -f "$RUN_DIR/steps/0-design/output.json" || { echo "the design step produced nothing"; exit 1; }
exit 0
