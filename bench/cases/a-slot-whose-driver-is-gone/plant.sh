#!/bin/sh
set -e
mkdir -p "$HOME/.config/agent-kit"
printf '[machine]\nmax_sessions = 1\n' > "$HOME/.config/agent-kit/config.toml"
# Above every Linux pid maximum, so nothing is running under it.
$KIT slot take --provider fake --slug a-ghost --step build --pid 4194305
# Read out of the ledger itself rather than through `machine`, which reaps
# before it prints: the thing this case plants is a row that any reader kills.
python3 - > "$BENCH/before" <<'PY'
import os, sqlite3
where = os.path.join(os.environ["XDG_STATE_HOME"], "agent-kit", "daemon.sqlite")
held = sqlite3.connect(where).execute("SELECT slug, pid FROM leases WHERE kind = 'session'").fetchall()
print(held)
PY
