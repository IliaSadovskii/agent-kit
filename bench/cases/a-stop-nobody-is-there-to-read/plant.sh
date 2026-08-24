#!/bin/sh
set -e
# A driver holds the run, somebody stops it, and that driver never comes back.
$KIT run new "$SLUG" --brief "a run that was stopped before this one" >/dev/null
$KIT slot hold --slug "$SLUG" --pid 1
$KIT run stop "$SLUG" "a stop nobody will ever read" > "$BENCH/stop-said" 2>&1
python3 - > "$BENCH/before" <<'PY'
import os, sqlite3
where = os.path.join(os.environ["XDG_STATE_HOME"], "agent-kit", "daemon.sqlite")
print(sqlite3.connect(where).execute("SELECT slug, what, reason FROM requests").fetchall())
PY
$KIT slot release --slug "$SLUG"
rm -rf .agent-kit/v3/runs
