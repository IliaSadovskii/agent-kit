#!/bin/sh
CONFIG="$BENCH/home/.config/agent-kit/config.toml"

shadowed() {
  WHERE=$(command -v "$1" 2>/dev/null)
  case "$WHERE" in
    "$BENCH/bin/"*) return 0 ;;
    *) echo "the trap was not planted: '$1' resolves to '${WHERE:-nothing at all}' rather than into this case's own bin — the real one reaches the network"; return 1 ;;
  esac
}

# --- the trap was standing, and it has two halves ---------------------------
# Both are needed and neither is enough. Without a provider that works there is
# no choice to make; without one that does not, there is nothing to wander off
# to. In a world with the shims taken away, `claude` answers nothing and this
# judge stops here rather than agreeing that the kit behaved.
shadowed claude || exit 1
claude --version >/dev/null 2>&1 ||
  { echo "the trap was not planted: the provider that must work does not answer"; exit 1; }
shadowed codex || exit 1
codex --version >/dev/null 2>&1 &&
  { echo "the trap was not planted: the provider that must be missing answers"; exit 1; }

# --- what the one that is missing would have told somebody to run -----------
INSTALL=$($PYTHON -c "from agent_kit.providers.registry import facts; print(' '.join(facts('codex').install))") ||
  { echo "the kit could not say how codex is installed"; exit 1; }
[ -n "$INSTALL" ] || { echo "codex declares no install command"; exit 1; }

# --- a bare walk, with nobody naming anything -------------------------------
# One line for the login it prints, and a second that answers nothing so an
# unexpected question lands somewhere a check can find it.
OUT=$(printf 'done\nNOT-AN-ANSWER-TO-ANYTHING\n' | $KIT setup 2>&1)
CODE=$?
[ "$CODE" = "0" ] || { echo "the bare walk exited $CODE: $OUT"; exit 1; }

printf '%s\n' "$OUT" | grep -qF "$INSTALL" &&
  { echo "the bare walk told somebody to install a provider they never named"; exit 1; }
[ -s "$BENCH/npm-argv" ] &&
  { echo "the bare walk ran an install command"; exit 1; }
grep -q "^\[providers.codex\]" "$CONFIG" 2>/dev/null &&
  { echo "the bare walk wrote down the provider that is not here"; exit 1; }
grep -q "^\[providers.claude_code\]" "$CONFIG" ||
  { echo "the bare walk did not write down the provider that works"; exit 1; }
grep -q "NOT-AN-ANSWER-TO-ANYTHING" "$CONFIG" &&
  { echo "the walk asked a question this case did not expect, and wrote the answer down"; exit 1; }
exit 0
