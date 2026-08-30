#!/bin/sh
CONFIG="$BENCH/home/.config/agent-kit/config.toml"

# --- the trap was standing --------------------------------------------------
[ -x "$BENCH/bin/npm" ] ||
  { echo "the trap was not planted: nothing shadows the installer, and the real one reaches the network"; exit 1; }

INSTALL=$($PYTHON -c "from agent_kit.providers.registry import facts; print(' '.join(facts('claude_code').install))") ||
  { echo "the kit could not say how claude_code is installed"; exit 1; }

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
