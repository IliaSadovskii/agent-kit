#!/bin/sh
# Ловушка сначала: вопрос ушёл владельцу, и назад пришло сообщение без единого
# слова. Судья, который читает только конец, зелёный и там, где никто ничего
# не присылал вовсе.
grep -q '2xdhdn' "$BENCH/owner.out" || { echo "the question never went out"; exit 1; }
test -s "$BENCH/owner.in" || { echo "nothing ever came back from the owner"; exit 1; }
grep -q '^#1[[:space:]]*$' "$BENCH/owner.in" ||
  { echo "what came back is not a reply with no text in it, so this measures nothing"; exit 1; }

# Пустое сообщение не ответ: вопрос кончился молчанием, и своим кодом.
grep -q '"how": "nobody-answered"' "$RUN_DIR/steps/0-design/asks.json" ||
  { echo "a message with no text in it settled the question"; exit 1; }
test ! -d "$RUN_DIR/steps/0-design/attempt-2" ||
  { echo "a second session was paid for a message that said nothing"; exit 1; }

# И умолчание, которого никто не подтвердил, дошло дорогим допущением: в вывод
# шага и оттуда в знание владельца.
grep -q '"expensive": true' "$RUN_DIR/steps/0-design/output.json" ||
  { echo "the default taken after a wordless reply is not an expensive assumption"; exit 1; }
grep -q 'Никто не ответил' docs/knowledge/entities.md ||
  { echo "the default nobody answered left no block in the knowledge"; exit 1; }
exit 0
