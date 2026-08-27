# The trap first: requests really was declared and really was measured as
# imported nowhere.
test -s "$INVENTORY" || { echo "no inventory was written"; exit 1; }
grep -q '"name": "requests"' "$INVENTORY" || { echo "requests was never declared here"; exit 1; }
grep -q '"module": "requests"' "$INVENTORY" && { echo "requests is imported after all"; exit 1; }

# Then the mechanism: a candidate list, one line per candidate, and a report
# that says which commit it measured.
test -s "$CANDIDATES" || { echo "no candidate list was written"; exit 1; }
grep -q '^- Убрать `requests`' "$CANDIDATES" || { echo "no line names requests"; cat "$CANDIDATES"; exit 1; }
grep -q "Это измерил кит" "$CANDIDATES" || { echo "the list does not say whose words these are"; exit 1; }
grep -q "Измерено на коммите" "$REPORT" || { echo "the report does not name the commit"; exit 1; }
exit 0
