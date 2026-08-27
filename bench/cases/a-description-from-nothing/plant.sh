#!/bin/sh
# A repository with no description at all, which is what a project looks like
# before anybody sits down with it.
set -e
rm -rf docs/knowledge
git add -A
git commit -q -m "a project nobody has described yet"
