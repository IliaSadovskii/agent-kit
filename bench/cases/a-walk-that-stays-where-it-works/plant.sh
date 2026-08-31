#!/bin/sh
set -e
mkdir -p "$BENCH/bin"

# One that works. This is the whole trap: without a working provider on this
# machine there is no choice to get wrong.
cat > "$BENCH/bin/claude" <<'INNER'
#!/bin/sh
if [ "$1" = "--version" ]; then echo "2.1.239 (Claude Code)"; exit 0; fi
cat > /dev/null
printf '%s\n' '{"type":"result","is_error":false,"result":"ok","session_id":"11111111-2222-3333-4444-555555555555","total_cost_usd":0.01}'
INNER
chmod +x "$BENCH/bin/claude"

# And one that does not, standing on PATH so that the world does not depend on
# whether the machine running the bench happens to have Codex installed.
cat > "$BENCH/bin/codex" <<'INNER'
#!/bin/sh
echo "codex: not installed on this machine" >&2
exit 127
INNER
chmod +x "$BENCH/bin/codex"

# An `npm` that refuses loudly. Nothing in this case should ever reach it: the
# walk has a working provider to take and no reason to print an install at all.
cat > "$BENCH/bin/npm" <<'INNER'
#!/bin/sh
printf '%s\n' "$@" >> "$BENCH/npm-argv"
echo "npm: this case should never have got here" >&2
exit 1
INNER
chmod +x "$BENCH/bin/npm"
