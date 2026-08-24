#!/bin/sh
test -s "$BENCH/owner.fail" || { echo "the channel was never made to fail"; exit 1; }
test -f "$XDG_CONFIG_HOME/agent-kit/config.toml" || { echo "no channel was configured, so nothing could fail"; exit 1; }

# Свой код, а не общий с молчанием: две тишины должны быть различимы утром.
grep -q '"how": "channel-failed"' "$RUN_DIR/steps/0-design/asks.json" ||
  { echo "a channel that could not be reached is not told apart from silence"; exit 1; }
if grep -q '"how": "nobody-answered"' "$RUN_DIR/steps/0-design/asks.json"; then
  echo "a broken channel was recorded as nobody answering"; exit 1
fi
grep -q '"expensive": true' "$RUN_DIR/steps/0-design/output.json" ||
  { echo "the default was taken and not written down as an expensive assumption"; exit 1; }
exit 0
