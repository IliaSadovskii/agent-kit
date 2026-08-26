#!/bin/sh
set -e
# Nobody's to delete: a directory at the path a worktree would be made at. The
# second feature is the one that meets it, so the first is already spawned and
# building by the time it does.
mkdir -p "$REPO/.agent-kit/v3/trees/two"
printf 'not a worktree\n' > "$REPO/.agent-kit/v3/trees/two/something"
