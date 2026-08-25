#!/bin/sh
# This session is alive while the skip is asked for, and it stays alive until
# the stop that the skip turned into is standing against this very run. Waiting
# for a moment instead — a sleep, a poll of the batch file — is a fixture that
# falls over whenever the machine is busy, which is the shape S7a wrote down.
n=0
while [ $n -lt 600 ]; do
  if python3 -c "
import os, sqlite3, sys
where = os.path.join(os.environ['XDG_STATE_HOME'], 'agent-kit', 'daemon.sqlite')
rows = sqlite3.connect(where).execute(
    \"SELECT 1 FROM requests WHERE slug = 'quote' AND what = 'stop'\"
).fetchall()
sys.exit(0 if rows else 1)
"; then
    printf 'stood\n' > "$BENCH/quote-saw-the-stop"
    printf 'QUOTE = 1\n' >> quote.py
    exit 0
  fi
  n=$((n + 1)); sleep 0.1
done
echo "no stop was ever posted against this run" >&2
exit 1
