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
# A judge that only checks nothing happened is green where nothing was planted.
shadowed claude || exit 1
claude --version >/dev/null 2>&1 &&
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
shadowed "${INSTALL%% *}" || exit 1

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
# asked about. A second line is fed that is not an answer to anything — if the
# walk asks a question this case did not expect, the word lands in the file and
# the check below finds it. One question too *many* is caught this way and one
# too many again by the EOF behind it; one question too *few* is not caught here
# at all, and the kit's stdin is buffered, so counting what was left unread
# would measure Python's buffer rather than the walk.
OUT=$(printf '\nNOT-AN-ANSWER-TO-ANYTHING\n' | $KIT setup claude_code 2>&1)
CODE=$?
[ "$CODE" = "0" ] || { echo "the second walk exited $CODE: $OUT"; exit 1; }
grep -q "NOT-AN-ANSWER-TO-ANYTHING" "$CONFIG" &&
  { echo "the walk asked a question this case did not expect, and wrote the answer down"; exit 1; }

grep -q "^\[providers.claude_code\]" "$CONFIG" ||
  { echo "the walk reached a working provider and wrote nothing down"; exit 1; }
grep -q 'provider = "claude_code"' "$CONFIG" ||
  { echo "nothing was written for a role the table does not name"; exit 1; }
printf '%s\n' "$OUT" | grep -q "provider check claude_code" ||
  { echo "the walk claimed the account without naming what measures it"; exit 1; }
exit 0
