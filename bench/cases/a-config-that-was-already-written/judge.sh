#!/bin/sh
CONFIG="$BENCH/home/.config/agent-kit/config.toml"

# --- the trap was standing --------------------------------------------------
# There really was a hand-written file here before the walk, and it really did
# hold the four things being asked about afterwards.
grep -q "^# ceilings I chose myself" "$CONFIG" ||
  { echo "the trap was not planted: no hand-written configuration was here"; exit 1; }
grep -q "^max_sessions = 7" "$CONFIG" ||
  { echo "the trap was not planted: the machine block was not the tuned one"; exit 1; }
grep -q "^\[roles.review\]" "$CONFIG" ||
  { echo "the trap was not planted: there was no role table to keep"; exit 1; }
grep -q "providers.claude_code" "$CONFIG" &&
  { echo "the trap was not planted: the block the walk writes was here already"; exit 1; }
"$BENCH/bin/claude" --version >/dev/null 2>&1 ||
  { echo "the trap was not planted: claude does not answer, so the walk never reaches the writing"; exit 1; }

# Two lines, and exactly two. The tool is already standing, so the install
# command is never printed and its line is never asked for; the login command is,
# and so is the pool — this machine already has a second provider configured, and
# that is the only condition under which the pool is a question at all.
OUT=$( printf '\n\n' | $KIT setup claude_code 2>&1 )
CODE=$?
[ "$CODE" = "0" ] || { echo "the walk exited $CODE: $OUT"; exit 1; }

grep -q "^\[providers.claude_code\]" "$CONFIG" ||
  { echo "the walk wrote no block of its own"; exit 1; }

# and everything that was there before it is still there
for KEPT in '^# ceilings I chose myself' '^max_sessions = 7' '^backoff = 0' \
            '^\[providers.fake\]' '^max_sessions = 1' '^\[roles.review\]'; do
  grep -q "$KEPT" "$CONFIG" ||
    { echo "the walk overwrote something it never asked about: $KEPT"; exit 1; }
done

# what it read back is what it wrote: a walk that leaves a file the kit cannot
# parse has broken the machine it was configuring
$KIT doctor >/dev/null 2>&1 || { echo "the configuration the walk left cannot be read"; exit 1; }
$KIT doctor 2>&1 | grep -q "unreadable-config" &&
  { echo "the configuration the walk left will not parse"; exit 1; }
exit 0
