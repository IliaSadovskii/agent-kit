#!/bin/sh
ROOM=.agent-kit/v3/sittings
# The trap first: a sitting really did happen and really did leave a room with
# an hour of somebody's speech in it, and somebody really did commit afterwards.
test -d "$ROOM" || { echo "the trap was not planted: no sitting was held"; exit 1; }
test -s "$ROOM"/*/telling.txt || { echo "the trap was not planted: nothing was said"; exit 1; }
git log --oneline main | grep -q 'что рассказал владелец' ||
  { echo "the trap was not planted: nobody committed after the sitting"; exit 1; }

FILES=$(git show --name-only --format= main)
# What they meant to commit.
echo "$FILES" | grep -q 'docs/knowledge/product.md' ||
  { echo "the description the sitting wrote did not reach the commit"; exit 1; }
# And what they did not: an hour of their own speech, their answers, and the raw
# text of every attempt.
echo "$FILES" | grep -q 'sittings' &&
  { echo "the room of the sitting went into the commit: $(echo "$FILES" | grep sittings | head -1)"; exit 1; }
git status --porcelain | grep -q 'sittings' &&
  { echo "the room is untracked and showing, so it is one `git add -A` from the history"; exit 1; }
exit 0
