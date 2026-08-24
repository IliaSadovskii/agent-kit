#!/bin/sh
# The trap first: a stop really was standing in the ledger, unread.
grep -q "$SLUG" "$BENCH/before" || { echo "no stop was ever posted"; exit 1; }
grep -q '^stop-asked:' "$BENCH/stop-said" || { echo "the stop went into the state, not the ledger"; exit 1; }

# And this run, which is not the one that was stopped, ran to the end.
test -f "$RUN_DIR/steps/0-design/output.json" || { echo "the design step produced nothing"; exit 1; }
grep -q 'stopped-by-request' "$RUN_DIR/run.json" &&
  { echo "a stop posted for a driver that died stopped a later run"; exit 1; }
exit 0
