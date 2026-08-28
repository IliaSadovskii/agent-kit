#!/bin/sh
set -e
# After the world's first commit, so the declaration is in the history exactly
# as it is anywhere else: what an older kit left behind is this one file.
printf '*\n' > .agent-kit/v3/.gitignore
