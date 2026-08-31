#!/bin/sh
CONFIG="$BENCH/home/.config/agent-kit/config.toml"

# What this judge measures is the kit against a declaration, and the declaration
# against the reference it was read from. It does not measure Codex CLI: the
# `codex` it talks to is a shim planted beside it. A refusal below means the kit
# stopped reading its own declaration — never that the real tool changed.

# --- the safety catch, and it measures what is about to run -----------------
# The word that will actually be executed, resolved the way the shell resolves
# it, has to land inside this case's own bin. Checking for "a file called npm"
# would stay green the day the declaration starts with `brew` or `curl`, and the
# judge would then run the real thing, network and all, on a disarmed run too.
shadowed() {
  WHERE=$(command -v "$1" 2>/dev/null)
  case "$WHERE" in
    "$BENCH/bin/"*) return 0 ;;
    *) echo "the trap was not planted: '$1' resolves to '${WHERE:-nothing at all}' rather than into this case's own bin — the real one reaches the network"; return 1 ;;
  esac
}

# --- the trap was standing --------------------------------------------------
shadowed codex || exit 1
codex --version >/dev/null 2>&1 &&
  { echo "the trap was not planted: codex answers before anybody installed it"; exit 1; }
grep -q "providers.codex" "$CONFIG" 2>/dev/null &&
  { echo "the trap was not planted: this machine already knows codex"; exit 1; }

# --- what the provider declares, asked of the kit ---------------------------
# Never written down here: a judge that checks a string it wrote itself is
# measuring its own typing.
INSTALL=$($PYTHON -c "from agent_kit.providers.registry import facts; print(' '.join(facts('codex').install))") ||
  { echo "the kit could not say how codex is installed"; exit 1; }
LOGIN=$($PYTHON -c "from agent_kit.providers.registry import facts; print(' '.join(facts('codex').login))") ||
  { echo "the kit could not say how codex is logged in"; exit 1; }
[ -n "$INSTALL" ] || { echo "codex declares no install command"; exit 1; }
[ -n "$LOGIN" ] || { echo "codex declares no login command"; exit 1; }
shadowed "${INSTALL%% *}" || exit 1

# --- the screen, on a machine where the tool does not work ------------------
# Two runs and not a pipeline: a pipeline's halves race, and the kit's blocking
# read gives no back-pressure on a line that fits in the pipe. Two runs are also
# what a person does — read the screen, go to the other terminal, come back.
SAID=$($KIT setup codex </dev/null 2>&1)
CODE=$?
[ "$CODE" = "8" ] ||
  { echo "the walk exited $CODE where a stream with nobody behind it is 8: $SAID"; exit 1; }
printf '%s\n' "$SAID" | grep -qF "$INSTALL" ||
  { echo "the walk did not print the install command this declaration carries"; exit 1; }
[ -s "$BENCH/npm-argv" ] &&
  { echo "the walk ran the install command itself"; exit 1; }
grep -q "providers.codex" "$CONFIG" 2>/dev/null &&
  { echo "the walk wrote a provider down before anybody installed it"; exit 1; }

# --- and then the person runs what it named ---------------------------------
$INSTALL >/dev/null 2>&1 || { echo "the command the kit printed did not run"; exit 1; }
[ -s "$BENCH/npm-argv" ] || { echo "the install command left no trace of running"; exit 1; }

# One line, and exactly one: the tool is standing now, so the install command is
# never printed again, and no second provider is configured, so the pool is not
# asked about. A second line is fed that answers nothing — if the walk asks a
# question this case did not expect, the word lands in the file and the check
# below finds it.
OUT=$(printf '\nNOT-AN-ANSWER-TO-ANYTHING\n' | $KIT setup codex 2>&1)
CODE=$?
[ "$CODE" = "0" ] || { echo "the second walk exited $CODE: $OUT"; exit 1; }
grep -q "NOT-AN-ANSWER-TO-ANYTHING" "$CONFIG" &&
  { echo "the walk asked a question this case did not expect, and wrote the answer down"; exit 1; }

# The login is printed, and it is this declaration's login rather than a
# sentence about logging in.
printf '%s\n' "$OUT" | grep -qF "$LOGIN" ||
  { echo "the walk did not print the login command this declaration carries"; exit 1; }

# And the kit ran neither of them. The shim writes down every argv it is given,
# so what the kit is allowed to have done to it is the free rung and nothing
# else: `--version`. A `login` line here is the kit logging somebody in.
grep -q "^login" "$BENCH/codex-argv" &&
  { echo "the walk ran the login command itself"; exit 1; }
grep -q -- "--version" "$BENCH/codex-argv" ||
  { echo "the walk never measured the tool it wrote down"; exit 1; }

grep -q "^\[providers.codex\]" "$CONFIG" ||
  { echo "the walk reached a working provider and wrote nothing down"; exit 1; }
printf '%s\n' "$OUT" | grep -q "provider check codex" ||
  { echo "the walk claimed the account without naming what measures it"; exit 1; }
exit 0
