#!/bin/sh
mkdir -p "$XDG_CONFIG_HOME/agent-kit"
cat > "$XDG_CONFIG_HOME/agent-kit/config.toml" <<TOML
[owner]
channel = "file"
file = "$BENCH/owner"
wait = 3
TOML
printf '/a 2xdhdn one per country\n' > "$BENCH/owner.in"
# Канал отдаёт ровно одно сообщение и падает на втором.
printf '1\n' > "$BENCH/owner.fail-after"
