#!/bin/sh
# Ловушка сначала: первый вопрос ушёл и на него ответили, а второй замысел
# действительно поднял что-то новое.
grep -q '2xdhdn' "$BENCH/owner.out" || { echo "the first question never went out"; exit 1; }
grep -q 'one per country, and Russia is 20' "$BENCH/owner.in" || { echo "no answer was ever planted"; exit 1; }
grep -q 'should a negative rate be refused' "$RUN_DIR/steps/0-design/attempt-2/raw.txt" ||
  { echo "the second design did not raise anything new"; exit 1; }

# Новый вопрос не отправляли: у владельца уже был круг.
if grep -q 'tqqzcs' "$BENCH/owner.out"; then echo "the owner was asked a second time in one run"; exit 1; fi

# И записан он своим кодом, а не кодом «никто не ответил»: сообщение не уходило,
# и утверждать в знании владельца, что его спросили, — неправда.
grep -q '"how": "had-their-round"' "$RUN_DIR/steps/0-design/asks.json" ||
  { echo "a question nobody was sent is recorded as one nobody answered"; exit 1; }
grep -q '"expensive": true' "$RUN_DIR/steps/0-design/output.json" ||
  { echo "the default taken without asking is not an expensive assumption"; exit 1; }
exit 0
