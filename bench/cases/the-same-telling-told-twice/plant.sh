#!/bin/sh
# The first sitting, so that the one the case drives is a second telling of the
# same thing. Its reply is written here rather than in `replies/`, because
# `replies/` is what the disarm takes away — and taking away the first sitting
# is exactly what should make this case go quiet.
set -e
cat > "$BENCH/first-reply.json" <<'JSON'
{
  "parts": [
    {"key": "money", "verdict": "unchanged"},
    {"key": "sign-in", "verdict": "new", "name": "вход", "says": "только Google", "said": "L2"}
  ],
  "ledger": [{"what": "импорт словаря еле ползёт", "kind": "badly", "said": "L4"}]
}
JSON
cat > "$BENCH/first-telling.txt" <<'TOLD'
Продукт — тренажёр английского.
Вход через Google и Apple, и почтой можно.
Уведомления вечером, окно человек выбирает сам.
Импорт словаря еле ползёт на больших файлах.
TOLD
$KIT -C "$REPO" knowledge tell --from "$BENCH/first-telling.txt" \
  --provider fake --option "reply=$BENCH/first-reply.json" >/dev/null
git add -A
git commit -q -m "the first telling"
