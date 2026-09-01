#!/bin/sh
# Ловушка сначала: строка вопроса стояла до прогона, названная чужим сообщением
# и часом, который давно прошёл.
test -s "$BENCH/ask-planted" || { echo "no question was planted before the run"; exit 1; }
# Идентификатор и номер сообщения — то, что подложил сам случай, а не слово,
# которым экран их подписывает: `message 99` мерило английскую прозу и покраснело
# на одном переводе, механизма не тронув.
grep -q '2xdhdn' "$BENCH/ask-planted" || { echo "the planted question was not written down"; exit 1; }
grep -qw '99' "$BENCH/ask-planted" || { echo "the planted question does not name the old message"; exit 1; }
# И она дожила до прогона: строка, которую выметут раньше, ничего не меряет.
grep -q '2xdhdn' "$BENCH/owner.out" || { echo "the question never went out at all"; exit 1; }
grep -q '^#1 ' "$BENCH/owner.in" || { echo "the planted answer is not a reply"; exit 1; }

grep -q '"how": "answered"' "$RUN_DIR/steps/0-design/asks.json" ||
  { echo "a reply to the message that just went out was not matched to its question"; exit 1; }
grep -q 'as the owner replied' "$RUN_DIR/steps/0-design/output.json" ||
  { echo "the design on file is not the one the reply produced"; exit 1; }
exit 0
