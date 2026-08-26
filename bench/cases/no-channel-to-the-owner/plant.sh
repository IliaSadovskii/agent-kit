#!/bin/sh
# Nothing about the owner is configured, on purpose, and this records that it
# was on purpose: a case that is green because a config file failed to be
# written is a case that measures nothing. The block, not the file — the world
# writes a `[machine]` block into every case, and this one is about `[owner]`.
CONFIG="$XDG_CONFIG_HOME/agent-kit/config.toml"
! grep -q '^\[owner\]' "$CONFIG" 2>/dev/null || exit 1
echo "no [owner] block anywhere" > "$BENCH/owner-was-never-configured"
