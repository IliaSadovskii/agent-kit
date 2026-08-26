#!/bin/sh
# The hook is written where a project becomes known to the kit, so the case
# runs the command a person would run rather than laying the file out itself.
set -e
$KIT init --force > "$BENCH/init-said" 2>&1

# Something worth pushing, on a branch that is not the trunk.
git checkout -q -b wip main
git commit -q --allow-empty -m "something worth pushing"
git checkout -q main

# And somewhere to force over: a commit the origin holds and `wip` does not.
git checkout -q --detach main
git commit -q --allow-empty -m "the commit a force push would drop"
git push -q origin HEAD:refs/heads/decoy
git checkout -q main

git -C "$ORIGIN" rev-parse main > "$BENCH/trunk-before"
git -C "$ORIGIN" rev-parse decoy > "$BENCH/decoy-before"
