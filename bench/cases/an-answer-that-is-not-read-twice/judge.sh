#!/bin/sh
grep -q '2xdhdn' "$BENCH/owner.in" || { echo "no answer was ever planted"; exit 1; }
grep -q '"how": "answered"' "$RUN_DIR/steps/0-design/asks.json" || { echo "the answer was never read"; exit 1; }

# Смещение сдвинулось: следующий опрос начинается не с начала ящика.
test -f "$XDG_STATE_HOME/agent-kit/daemon.sqlite" || { echo "no ledger to hold an offset"; exit 1; }
OFFSET=$(python3 -c "import sqlite3,sys; db=sqlite3.connect(sys.argv[1]); r=db.execute(\"SELECT value FROM channel WHERE what='offset'\").fetchone(); print(r[0] if r else '')" "$XDG_STATE_HOME/agent-kit/daemon.sqlite")
test -n "$OFFSET" || { echo "the offset was never written down, so an answer can be read twice"; exit 1; }
test "$OFFSET" != "0" || { echo "the offset stayed at the start of the inbox"; exit 1; }
exit 0
