#!/bin/sh
set -e
# Everything this case needs is planted, and nothing about the machine the
# bench happens to be running on is assumed. The world inherits that machine's
# PATH, so both a real `npm` and a real `claude` may be standing on it: a
# pre-check that read *`claude` is absent* would be red here, and an install
# command that reached the real `npm` would go to the network.
mkdir -p "$BENCH/bin"

# What a working Claude Code looks like. Prepared here so the installer below
# has a file to copy rather than a heredoc inside a heredoc.
cat > "$BENCH/claude-once-installed" <<'SH'
#!/bin/sh
if [ "$1" = "--version" ]; then echo "2.1.239 (Claude Code)"; exit 0; fi
cat > /dev/null
printf '%s\n' '{"type":"result","is_error":false,"result":"ok","session_id":"11111111-2222-3333-4444-555555555555","total_cost_usd":0.01}'
SH
chmod +x "$BENCH/claude-once-installed"

# And what it looks like before anybody installs it: on PATH, answering nothing.
cat > "$BENCH/bin/claude" <<'SH'
#!/bin/sh
echo "claude: not installed on this machine" >&2
exit 127
SH
chmod +x "$BENCH/bin/claude"

# `npm` is the first word of the command `claude_code` declares. This one
# writes down that it ran and puts the tool where the real one would.
cat > "$BENCH/bin/npm" <<'SH'
#!/bin/sh
printf '%s\n' "$@" >> "$BENCH/npm-argv"
cp "$BENCH/claude-once-installed" "$BENCH/bin/claude"
SH
chmod +x "$BENCH/bin/npm"

# A machine with nothing on it: the world names `fake` as its default provider
# and this case is about the one that has none, so the line goes.
cat > "$BENCH/home/.config/agent-kit/config.toml" <<'SH'
[machine]
backoff = 0
SH
