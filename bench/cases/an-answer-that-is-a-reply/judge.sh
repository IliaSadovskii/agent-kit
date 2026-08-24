#!/bin/sh
# Ловушка сначала: ответ был реплаем, а не набранным идентификатором.
grep -q '^#1 ' "$BENCH/owner.in" || { echo "the planted answer is not a reply"; exit 1; }
if grep -q '2xdhdn' "$BENCH/owner.in"; then echo "the answer names the question, so this measures nothing"; exit 1; fi
grep -q '2xdhdn' "$BENCH/owner.out" || { echo "the question never went out"; exit 1; }

grep -q '"how": "answered"' "$RUN_DIR/steps/0-design/asks.json" ||
  { echo "a reply to the message was not matched to its question"; exit 1; }
grep -q 'as the owner replied' "$RUN_DIR/steps/0-design/output.json" ||
  { echo "the design on file is not the one the reply produced"; exit 1; }
exit 0
