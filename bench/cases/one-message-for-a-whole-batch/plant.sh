#!/bin/sh
mkdir -p "$XDG_CONFIG_HOME/agent-kit"
cat > "$XDG_CONFIG_HOME/agent-kit/config.toml" <<TOML
[owner]
channel = "file"
file = "$BENCH/owner"
wait = 2
TOML
test ! -e "$BENCH/owner.out" || exit 1
echo "the channel was empty before the batch" > "$BENCH/owner-was-clean"
