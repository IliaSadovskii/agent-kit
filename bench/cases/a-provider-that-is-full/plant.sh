#!/bin/sh
set -e
mkdir -p "$HOME/.config/agent-kit"
# Four sessions allowed here, and one of them on `fake`. The machine is not the
# thing in the way, so a kit that only counts the machine lets this run through.
printf '[machine]\nmax_sessions = 4\n\n[providers.fake]\nmax_sessions = 1\n' \
  > "$HOME/.config/agent-kit/config.toml"
$KIT slot take --provider fake --slug somebody-else --step build --pid 1
