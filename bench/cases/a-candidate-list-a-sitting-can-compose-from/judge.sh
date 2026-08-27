# The trap first: requests really was declared and really was measured as
# imported nowhere, and ruff really is a second declared package.
test -s "$INVENTORY" || { echo "no inventory was written"; exit 1; }
grep -q '"name": "requests"' "$INVENTORY" || { echo "requests was never declared here"; exit 1; }
grep -q '"name": "ruff"' "$INVENTORY" || { echo "ruff was never declared here"; exit 1; }
grep -q '"module": "requests"' "$INVENTORY" && { echo "requests is imported after all"; exit 1; }

# Then the mechanism: a candidate list, one line per candidate, and a report
# that says which commit it measured.
test -s "$CANDIDATES" || { echo "no candidate list was written"; exit 1; }
grep -q '^- Убрать `requests`' "$CANDIDATES" || { echo "no line names requests"; cat "$CANDIDATES"; exit 1; }
grep -q "Это измерил кит" "$CANDIDATES" || { echo "the list does not say whose words these are"; exit 1; }
grep -q "Измерено на коммите" "$REPORT" || { echo "the report does not name the commit"; exit 1; }

# And the two counts no program can check reach the report as numbers, not as
# rows somebody has to add up.
grep -q "Используется без импорта: 1" "$REPORT" || {
  echo "the report does not count what is used without importing"; grep "Найдено" "$REPORT"; exit 1; }
grep -q "Привязано по слову сессии: 1" "$REPORT" || {
  echo "the report does not count what is held under another name"; grep "Найдено" "$REPORT"; exit 1; }
exit 0
