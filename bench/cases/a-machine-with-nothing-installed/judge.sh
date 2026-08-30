#!/bin/sh
CONFIG="$BENCH/home/.config/agent-kit/config.toml"

# --- the trap was standing --------------------------------------------------
# A judge that only checks nothing happened is green where nothing was planted.
[ -x "$BENCH/bin/npm" ] ||
  { echo "the trap was not planted: nothing shadows the installer, and the real one reaches the network"; exit 1; }
"$BENCH/bin/claude" --version >/dev/null 2>&1 &&
  { echo "the trap was not planted: claude answers before anybody installed it"; exit 1; }
grep -q "providers.claude_code" "$CONFIG" 2>/dev/null &&
  { echo "the trap was not planted: this machine already knows claude_code"; exit 1; }
grep -q "^provider" "$CONFIG" 2>/dev/null &&
  { echo "the trap was not planted: this machine already names a provider"; exit 1; }

# --- what the provider declares, asked of the kit ---------------------------
# Never written down here: a judge that checks a string it wrote itself is
# measuring its own typing.
INSTALL=$($PYTHON -c "from agent_kit.providers.registry import facts; print(' '.join(facts('claude_code').install))") ||
  { echo "the kit could not say how claude_code is installed"; exit 1; }
[ -n "$INSTALL" ] || { echo "claude_code declares no install command"; exit 1; }

# --- the screen, on a machine where the tool does not work ------------------
# Two runs and not a pipeline: a pipeline's halves race, and the kit's blocking
# read gives no back-pressure on a line that fits in the pipe. Two runs are also
# what a person does — read the screen, go to the other terminal, come back.
SAID=$($KIT setup claude_code </dev/null 2>&1)
CODE=$?
[ "$CODE" = "8" ] ||
  { echo "the walk exited $CODE where a stream with nobody behind it is 8: $SAID"; exit 1; }
printf '%s\n' "$SAID" | grep -qF "$INSTALL" ||
  { echo "the walk did not print the command the provider declares"; exit 1; }
[ -s "$BENCH/npm-argv" ] &&
  { echo "the walk ran the install command itself"; exit 1; }
grep -q "providers.claude_code" "$CONFIG" 2>/dev/null &&
  { echo "the walk wrote a provider down before anybody installed it"; exit 1; }

# --- and then the person runs what it named ---------------------------------
$INSTALL >/dev/null 2>&1 || { echo "the command the kit printed did not run"; exit 1; }
[ -s "$BENCH/npm-argv" ] || { echo "the install command left no trace of running"; exit 1; }

# One line, and exactly one: the tool is standing now, so the install command is
# never printed again, and no second provider is configured, so the pool is not
# asked about.
OUT=$(printf '\n' | $KIT setup claude_code 2>&1)
CODE=$?
[ "$CODE" = "0" ] || { echo "the second walk exited $CODE: $OUT"; exit 1; }

grep -q "^\[providers.claude_code\]" "$CONFIG" ||
  { echo "the walk reached a working provider and wrote nothing down"; exit 1; }
grep -q 'provider = "claude_code"' "$CONFIG" ||
  { echo "nothing was written for a role the table does not name"; exit 1; }
printf '%s\n' "$OUT" | grep -q "provider check claude_code" ||
  { echo "the walk claimed the account without naming what measures it"; exit 1; }
exit 0
