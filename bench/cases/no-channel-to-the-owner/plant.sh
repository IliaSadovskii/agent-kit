#!/bin/sh
# Nothing is configured, on purpose, and this records that it was on purpose:
# a case that is green because a config file failed to be written is a case
# that measures nothing.
test ! -f "$XDG_CONFIG_HOME/agent-kit/config.toml" || exit 1
echo "no [owner] block anywhere" > "$BENCH/owner-was-never-configured"
