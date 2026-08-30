#!/bin/sh
set -e
mkdir -p "$BENCH/bin"

cat > "$BENCH/claude-once-installed" <<'SH'
#!/bin/sh
if [ "$1" = "--version" ]; then echo "2.1.239 (Claude Code)"; exit 0; fi
cat > /dev/null
printf '%s\n' '{"type":"result","is_error":false,"result":"ok","session_id":"11111111-2222-3333-4444-555555555555"}'
SH
chmod +x "$BENCH/claude-once-installed"
cp "$BENCH/claude-once-installed" "$BENCH/bin/claude"

# A configuration a person wrote, with the things a person puts in one: a
# comment of their own, a machine block they tuned, a provider block for
# something else, and a role table. The walk is about to touch none of it.
#
# It carries `provider = "fake"` because the world's own configuration does and
# this file replaces it whole — a case that plants a config.toml and drops that
# line would be measuring the door's first rung by accident.
cat > "$BENCH/home/.config/agent-kit/config.toml" <<'SH'
# ceilings I chose myself, and the comment that says why
[machine]
max_sessions = 7
backoff = 0
provider = "fake"

[providers.fake]
enabled = true
max_sessions = 1

[roles.review]
provider = "fake"
SH
