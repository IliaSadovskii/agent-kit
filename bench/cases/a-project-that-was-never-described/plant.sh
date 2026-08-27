#!/bin/sh
# The baseline is a described project, like every ordinary one. This takes the
# description away and leaves the declaration saying there should be one, which
# is the silence the second version answered zero to.
set -e
rm -rf docs/knowledge
git add -A
git commit -q -m "a project that says it is described and is not"
