#!/bin/sh
# Ловушка сначала: прогон действительно встал на закрытом гейте, и дальше него
# не ушло ничего. Судья, который сверяет только конец, зелёный и там, где
# останавливать было нечего.
CASE=$(dirname "$0")
grep -q '"passed": false' "$RUN_DIR/steps/2-verify/output.json" ||
  { echo "verify did not record a red suite, so nothing stopped this run"; exit 1; }
test ! -d "$RUN_DIR/steps/5-deliver" || { echo "delivery ran for a run that stopped"; exit 1; }
test -z "$(find "$BENCH" -maxdepth 1 -name 'gh-opened-*' -print -quit)" ||
  { echo "a pull request was opened for a run that stopped"; exit 1; }

# Утро: владелец чинит тесты руками и просит прогон продолжить.
printf '#!/bin/sh\nexit 0\n' > check.sh
$KIT run reopen add-vat > "$BENCH/reopened" 2>&1 ||
  { echo "a stopped run has no way on: $(tail -1 "$BENCH/reopened")"; exit 1; }
$KIT run go add-vat --provider fake --option "reply=$CASE/replies/03-reply.json" > "$BENCH/carried-on" 2>&1 ||
  { echo "the reopened run did not go on: $(tail -1 "$BENCH/carried-on")"; exit 1; }

# Он пошёл с того шага, на котором встал: verify измерил починенные тесты
# заново, и прогон дошёл до конца.
test -d "$RUN_DIR/steps/2-verify/attempt-2" ||
  { echo "the step that stopped the run was not the step it went on from"; exit 1; }
grep -q '"passed": true' "$RUN_DIR/steps/2-verify/output.json" ||
  { echo "verify did not measure what the owner put right"; exit 1; }
grep -q '"status": "done"' "$RUN_DIR/run.json" || { echo "the reopened run did not reach its end"; exit 1; }
test -f "$BENCH/gh-opened-kit-add-vat" || { echo "the run that went on opened no pull request"; exit 1; }

# И ничего из того, что прошло, не оплачено второй сессией.
test ! -d "$RUN_DIR/steps/0-design/attempt-2" || { echo "the design was paid for a second time"; exit 1; }
test ! -d "$RUN_DIR/steps/1-build/attempt-2" || { echo "the build was paid for a second time"; exit 1; }
exit 0
