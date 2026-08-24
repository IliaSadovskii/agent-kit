#!/bin/sh
test -s "$BENCH/owner.fail" || { echo "the channel was never made to fail"; exit 1; }
test -f "$XDG_CONFIG_HOME/agent-kit/config.toml" || { echo "no channel was configured, so nothing could fail"; exit 1; }

grep -q '"how": "channel-failed"' "$RUN_DIR/steps/0-design/asks.json" ||
  { echo "a channel that could not be reached is not told apart from silence"; exit 1; }
grep -q 'спросить владельца не вышло' "$RUN_DIR/steps/0-design/output.json" ||
  { echo "the record does not say which of the two silences this was"; exit 1; }
exit 0
