#!/bin/sh
set -e
# The world's own configuration names a provider, because every world can run
# one. This case takes that away and nothing else: a machine that has a kit and
# no agent, which is the machine S9a exists for.
cat > "$BENCH/home/.config/agent-kit/config.toml" <<'SH'
[machine]
backoff = 0
SH
