#!/bin/sh
set -e
mkdir -p "$HOME/.config/agent-kit"
# One second, doubling to two. The number is the machine's, and the bench must
# not sit through the one a real night uses: what this case measures is that
# there is a pause and that it grows, not how many seconds it is.
printf '[machine]\nbackoff = 1\n' > "$HOME/.config/agent-kit/config.toml"
