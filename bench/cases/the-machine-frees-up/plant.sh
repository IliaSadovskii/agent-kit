#!/bin/sh
set -e
mkdir -p "$HOME/.config/agent-kit"
printf '[machine]\nmax_sessions = 1\n' > "$HOME/.config/agent-kit/config.toml"
date +%s > "$BENCH/planted-at"
printf 6 > "$BENCH/ttl"
# Alive, so it is not reaped, and short-lived, so it goes away on its own.
$KIT slot take --provider fake --slug somebody-else --step build --pid 1 --ttl 6
