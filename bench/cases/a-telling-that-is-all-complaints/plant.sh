#!/bin/sh
# A repository nobody has described, so that what the sitting writes is the only
# thing there is to answer the question afterwards.
set -e
rm -rf docs/knowledge
git add -A
git commit -q -m "a project nobody has described yet"
