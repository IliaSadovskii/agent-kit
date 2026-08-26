#!/bin/sh
# Ловушка сначала: остановка действительно дошла до прогона, который шёл, и
# увела за собой то, что его ждало.
CASE=$(dirname "$0")
RUNS="$REPO/.agent-kit/v3/runs"
test -s "$BENCH/rates-saw-the-stop" || { echo "the stop never stood against the running feature"; exit 1; }
grep -q 'stopped-by-request' "$RUNS/rates/run.json" || { echo "the run does not say a person stopped it"; exit 1; }
grep -q 'needed-rates' "$BATCH_FILE" || { echo "quote was not taken down by rates, so there is no chain here"; exit 1; }
test -z "$(find "$BENCH" -maxdepth 1 -name 'gh-opened-*' -print -quit)" ||
  { echo "a pull request was opened on a night that stopped"; exit 1; }

# Утро: владелец возвращает фичу, и ему сразу сказано, что вернулась не одна.
$KIT -C "$REPO" batch reopen vat rates > "$BENCH/reopened" 2>&1 ||
  { echo "a stopped feature has no way back: $(tail -1 "$BENCH/reopened")"; exit 1; }
grep -q 'quote' "$BENCH/reopened" || { echo "what rates took down was not said at the moment it was typed"; exit 1; }

$KIT -C "$REPO" batch go vat --provider fake \
  --option "rates:reply=$CASE/replies/rates/03-review.json" \
  --option "quote:reply=$CASE/replies/quote/01-design.json" \
  --option "quote:reply=$CASE/replies/quote/02-build.json" \
  --option "quote:reply=$CASE/replies/quote/03-review.json" > "$BENCH/second-night" 2>&1 ||
  { echo "the batch did not carry on: $(tail -1 "$BENCH/second-night")"; exit 1; }

# Обе фичи вышли, и та, что стояла ночью, пошла с того шага, где встала.
grep -q '"slug": "rates",' "$BATCH_FILE" || { echo "the batch file lost rates"; exit 1; }
python3 - <<'PY' || exit 1
import json, os, sys
held = json.load(open(os.environ["BATCH_FILE"], encoding="utf-8"))
where = {feature["slug"]: feature["status"] for feature in held["features"]}
if where != {"rates": "done", "quote": "done"}:
    print(f"the morning left {where}")
    sys.exit(1)
PY
test ! -d "$RUNS/rates/steps/0-design/attempt-2" || { echo "the design of a feature that had passed it was paid for twice"; exit 1; }
test ! -d "$RUNS/rates/steps/1-build/attempt-2" || { echo "the build of a feature that had passed it was paid for twice"; exit 1; }
test -f "$BENCH/gh-opened-kit-rates" || { echo "rates opened no pull request"; exit 1; }
test -f "$BENCH/gh-opened-kit-quote" || { echo "quote opened no pull request"; exit 1; }
exit 0
