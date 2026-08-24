#!/bin/sh
set -e
mkdir -p "$HOME/.config/agent-kit"
printf '[machine]\nmax_sessions = 1\n' > "$HOME/.config/agent-kit/config.toml"
date +%s > "$BENCH/planted-at"
# Ten minutes: longer than the wait, so what ends the wait is the ceiling on it.
$KIT slot take --provider fake --slug somebody-else --step build --pid 1 --ttl 600
