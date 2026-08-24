#!/bin/sh
set -e
mkdir -p "$HOME/.config/agent-kit"
printf '[machine]\nmax_sessions = 1\n' > "$HOME/.config/agent-kit/config.toml"
# Held by pid 1, which is alive and is not this run: a lease of a live driver.
$KIT slot take --provider fake --slug somebody-else --step build --pid 1
