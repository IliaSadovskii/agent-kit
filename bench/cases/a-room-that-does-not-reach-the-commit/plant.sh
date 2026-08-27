#!/bin/sh
# A sitting, and then what the kit itself tells the owner to do: read the diff
# and commit it. `git add -A` is exactly what they will type.
set -e
cat > "$BENCH/telling.txt" <<'TOLD'
Продукт — тренажёр английского.
Вход через Google и Apple, и почтой можно.
TOLD
cat > "$BENCH/reply.json" <<'JSON'
{
  "parts": [
    {"key": "money", "verdict": "unchanged"},
    {"key": "sign-in", "verdict": "new", "name": "вход", "says": "Google, Apple и почта", "said": "L2"}
  ],
  "ledger": []
}
JSON
$KIT -C "$REPO" knowledge tell --from "$BENCH/telling.txt" \
  --provider fake --option "reply=$BENCH/reply.json" >/dev/null
git add -A
git commit -q -m "что рассказал владелец"
