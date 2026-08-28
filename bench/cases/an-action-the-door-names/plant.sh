#!/bin/sh
set -e
# A second project, beside the world rather than inside it: this case is about
# a project with nothing else standing, and the world's own is about to get a run.
QUIET="$BENCH/quiet"
mkdir -p "$QUIET"
cp -R "$REPO/.agent-kit" "$REPO/docs" "$REPO/check.sh" "$REPO/money.py" "$QUIET/"
rm -rf "$QUIET/.agent-kit/v3/runs" "$QUIET/.agent-kit/v3/batches"
cat > "$QUIET/.agent-kit/v3/manual.md" <<'MD'
# Сделать руками

- положить ключ в окружение · `key: aaaaaa` · `proof: sh ops/has-key.sh`
MD
cd "$QUIET"
git init -q -b main
git add -A
git commit -qm "a project with one thing left for a person"
