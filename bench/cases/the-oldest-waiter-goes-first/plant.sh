#!/bin/sh
set -e
mkdir -p "$HOME/.config/agent-kit"
# One session at a time, and this run is on an account of its own — so what
# holds it back can only be the machine's own ceiling.
cat > "$HOME/.config/agent-kit/config.toml" <<TOML
[machine]
max_sessions = 1

[providers.fake]
account = "ours"
TOML
# The slot is held, and it comes free well inside this case's wait.
$KIT slot take --provider fake --account theirs --slug somebody-else --step build --pid 1 --ttl 3
# And somebody on another account asked for the machine before we did.
$KIT slot wants --provider fake --account theirs --slug asked-first --step build --pid 1
python3 - > "$BENCH/before" <<PY
import os, sqlite3
where = os.path.join(os.environ["XDG_STATE_HOME"], "agent-kit", "daemon.sqlite")
db = sqlite3.connect(where)
print(db.execute("SELECT slug, account FROM waiters").fetchall())
print(db.execute("SELECT slug FROM leases WHERE kind = 'session'").fetchall())
PY
