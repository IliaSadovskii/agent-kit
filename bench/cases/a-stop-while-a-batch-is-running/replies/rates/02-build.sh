#!/bin/sh
# A person, from another terminal, while this session is running.
$KIT -C "$REPO" batch stop vat "enough for tonight" > "$BENCH/stop-said" 2>&1
# And this session stays alive until that stop is standing against its own run,
# so what the case measures is the stop rather than a lucky moment.
n=0
while [ $n -lt 600 ]; do
  if python3 -c "
import os, sqlite3, sys
where = os.path.join(os.environ['XDG_STATE_HOME'], 'agent-kit', 'daemon.sqlite')
rows = sqlite3.connect(where).execute(
    \"SELECT 1 FROM requests WHERE slug = 'rates' AND what = 'stop'\"
).fetchall()
sys.exit(0 if rows else 1)
"; then
    printf 'stood\n' > "$BENCH/rates-saw-the-stop"
    printf 'RATE = 20\n' >> rates.py
    exit 0
  fi
  n=$((n + 1)); sleep 0.1
done
echo "no stop ever reached this run" >&2
exit 1
