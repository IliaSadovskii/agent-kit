#!/bin/sh
set -e
mkdir -p "$HOME/.config/agent-kit"
# `wait = 0` is the child refusing rather than queueing: this case is about what
# the batch above it does with the refusal, not about how long a run waits.
printf '[machine]\nmax_sessions = 1\nwait    = 0\n' > "$HOME/.config/agent-kit/config.toml"
# Held by pid 1, which is alive and is not this batch: a lease of a live driver.
$KIT slot take --provider fake --slug somebody-else --step build --pid 1
