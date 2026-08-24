#!/bin/sh
mkdir -p "$XDG_CONFIG_HOME/agent-kit"
cat > "$XDG_CONFIG_HOME/agent-kit/config.toml" <<TOML
[owner]
channel = "file"
file = "$BENCH/owner"
wait = 2
TOML
printf '/a zzzzzz A-STRAY-ANSWER\n' > "$BENCH/owner.in"
