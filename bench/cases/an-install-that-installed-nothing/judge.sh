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
# Both halves of it. The tool that must stay broken is asked for as well as the
# installer that must stay a script: without the first, PATH reaches the real
# `claude` on whatever machine the bench is running on and the kit starts it.
shadowed claude || exit 1

INSTALL=$($PYTHON -c "from agent_kit.providers.registry import facts; print(' '.join(facts('claude_code').install))") ||
  { echo "the kit could not say how claude_code is installed"; exit 1; }
[ -n "$INSTALL" ] || { echo "claude_code declares no install command"; exit 1; }
shadowed "${INSTALL%% *}" || exit 1

OUT=$( { $INSTALL >/dev/null 2>&1; printf '\n\n'; } | $KIT setup claude_code 2>&1 )
CODE=$?

# The mark, and it is the first thing judged: the lying installer really did
# run and really did exit zero. A judge that went straight to *nothing was
# written* would be green on a machine where the walk was never taken.
[ -s "$BENCH/npm-argv" ] ||
  { echo "the trap was not armed: the install command never ran, so nothing lied"; exit 1; }

[ "$CODE" = "4" ] || { echo "the walk exited $CODE where an unusable provider is 4: $OUT"; exit 1; }
printf '%s\n' "$OUT" | grep -q "provider-not-ready" ||
  { echo "the walk did not refuse by name"; exit 1; }
grep -q "providers.claude_code" "$CONFIG" 2>/dev/null &&
  { echo "the walk wrote down a provider that is not there"; exit 1; }
exit 0
