#!/bin/sh
# Ловушка сначала: первый вопрос действительно ушёл, а канал действительно лёг.
grep -q '2xdhdn' "$BENCH/owner.out" || { echo "the first question never went out"; exit 1; }
test -s "$BENCH/owner.fail-after" || { echo "the channel was never made to fall over"; exit 1; }
test "$(grep -c '^--- ' "$BENCH/owner.out")" = "1" ||
  { echo "the channel did not fall over midway: it sent more than one question"; exit 1; }

# Ответ на ушедший вопрос взят, а не выброшен вместе с недоставленным.
grep -q '"how": "answered"' "$RUN_DIR/steps/0-design/asks.json" ||
  { echo "the answer to a question already on the phone was thrown away"; exit 1; }
grep -q '"how": "channel-failed"' "$RUN_DIR/steps/0-design/asks.json" ||
  { echo "the question that never went out is not recorded as one the channel lost"; exit 1; }
exit 0
