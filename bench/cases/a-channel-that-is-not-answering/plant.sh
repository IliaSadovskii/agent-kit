#!/bin/sh
mkdir -p "$XDG_CONFIG_HOME/agent-kit"
cat > "$XDG_CONFIG_HOME/agent-kit/config.toml" <<TOML
[owner]
channel = "file"
file = "$BENCH/owner"
wait = 2
TOML
printf 'the bot token is wrong\n' > "$BENCH/owner.fail"
