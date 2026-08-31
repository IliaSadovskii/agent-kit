#!/bin/sh
CONFIG="$BENCH/home/.config/agent-kit/config.toml"
# --- the safety catch, and it measures what is about to run -----------------
# Not "a file called npm exists": the first word comes out of the kit on
# purpose, so the day a provider declares `brew`, `pnpm`, `curl` or `uv` a
# check on the old name would stay green while the judge ran the real thing —
# on a disarmed world too, where nothing shadows it. What is asked is the word
# that will actually be executed, resolved the way the shell will resolve it,
# and it has to land inside this case's own bin.
shadowed() {
  WHERE=$(command -v "$1" 2>/dev/null)
  case "$WHERE" in
    "$BENCH/bin/"*) return 0 ;;
    *) echo "the trap was not planted: '$1' resolves to '${WHERE:-nothing at all}' rather than into this case's own bin — the real one reaches the network"; return 1 ;;
  esac
}

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
shadowed claude || exit 1
claude --version >/dev/null 2>&1 ||
  { echo "the trap was not planted: claude does not answer, so the walk never reaches the writing"; exit 1; }

# Two lines, and exactly two. The tool is already standing, so the install
# command is never printed and its line is never asked for; the login command is,
# and so is the pool — this machine already has a second provider configured, and
# that is the only condition under which the pool is a question at all.
# A third line is fed that is not an answer to anything: if the walk asks a
# question this case did not expect, the word lands in the file below.
OUT=$( printf '\n\nNOT-AN-ANSWER-TO-ANYTHING\n' | $KIT setup claude_code 2>&1 )
CODE=$?
[ "$CODE" = "0" ] || { echo "the walk exited $CODE: $OUT"; exit 1; }
grep -q "NOT-AN-ANSWER-TO-ANYTHING" "$CONFIG" &&
  { echo "the walk asked a question this case did not expect, and wrote the answer down"; exit 1; }

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
# One question and not two: `doctor` refuses a configuration it cannot parse, so
# a second line looking for the code in its output could never be reached.
$KIT doctor >/dev/null 2>&1 || { echo "the configuration the walk left cannot be read"; exit 1; }
exit 0
