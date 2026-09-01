#!/bin/sh
# What this judge measures is the kit against a declaration and against the
# output the owner's own machine printed. It does not measure Codex CLI: the
# `codex` it talks to is a shim planted beside it. A refusal below means the kit
# stopped reading its own declaration — never that the real tool changed.

OUT_OF=$BENCH/codex-loggedout
WORKING=$BENCH/codex-working

# --- the safety catch, and it measures what is about to run -----------------
# Both shims have to be inside this case's own room. A `codex` anywhere else is
# somebody's real tool with somebody's real account and somebody's real quota.
for SHIM in "$OUT_OF" "$WORKING"; do
  case "$SHIM" in
    "$BENCH"/*) ;;
    *) echo "the trap was not planted: '$SHIM' is outside this case's own room"; exit 1 ;;
  esac
  [ -x "$SHIM" ] || { echo "the trap was not planted: '$SHIM' is not there"; exit 1; }
done
WHERE=$(command -v codex 2>/dev/null)
case "$WHERE" in
  "$BENCH/bin/"*) ;;
  *) echo "the trap was not planted: bare 'codex' resolves to '${WHERE:-nothing at all}' rather than into this case's own bin"; exit 1 ;;
esac

# --- the trap was standing --------------------------------------------------
# The tool is installed and it answers: that is the whole point of this shape,
# and a case that skipped it would be green against a `codex` that is missing.
"$OUT_OF" --version >/dev/null 2>&1 ||
  { echo "the trap was not planted: the shim does not answer --version, so this is not 'installed'"; exit 1; }
SAID=$(echo | "$OUT_OF" exec 2>&1)
[ $? = 0 ] &&
  { echo "the trap was not planted: the logged-out shim did not fail"; exit 1; }
printf '%s\n' "$SAID" | grep -q "401 Unauthorized" ||
  { echo "the trap was not planted: the logged-out shim never says what the owner's machine said"; exit 1; }
printf '%s\n' "$SAID" | grep -q "banner line 1$" ||
  { echo "the trap was not planted: the shim prints no run-up, so nothing here measures which end is kept"; exit 1; }

# --- what the provider declares, asked of the kit ---------------------------
# Never written down here: a judge that checks a string it wrote itself is
# measuring its own typing.
LOGIN=$($PYTHON -c "from agent_kit.providers.registry import facts; print(' '.join(facts('codex').login))") ||
  { echo "the kit could not say how codex is logged in"; exit 1; }
[ -n "$LOGIN" ] || { echo "codex declares no login command"; exit 1; }

# --- the control: the same command, and an account that answers -------------
OUT=$($KIT provider check codex --option "binary=$WORKING" 2>&1)
CODE=$?
[ "$CODE" = "0" ] ||
  { echo "the trap was not armed: the same command refuses even a tool with an account ($CODE): $OUT"; exit 1; }
printf '%s\n' "$OUT" | grep -qE "^ +ok +login" ||
  { echo "the trap was not armed: an account that answered did not pass the rung about the account: $OUT"; exit 1; }

# --- and the one with no account behind it ----------------------------------
OUT=$($KIT provider check codex --option "binary=$OUT_OF" 2>&1)
CODE=$?
[ "$CODE" = "4" ] ||
  { echo "the ladder exited $CODE where a provider that earned no level is 4: $OUT"; exit 1; }
printf '%s\n' "$OUT" | grep -q "provider-not-ready" ||
  { echo "the ladder did not refuse by name"; exit 1; }

# The rung, by the kit's own name for it and in the backticks it is printed in.
# This is the whole of the first defect: the ladder used to print `ok` here and
# stop on `one_shot`, which is a rung it had not measured.
printf '%s\n' "$OUT" | grep -qF '`login`' ||
  { echo "the ladder stopped somewhere other than the rung about the account: $OUT"; exit 1; }
printf '%s\n' "$OUT" | grep -qE "^ +ok +login" &&
  { echo "the rung about the account passed for an account that never answered: $OUT"; exit 1; }

# --- the reason reached the screen, and it is the end of it -----------------
printf '%s\n' "$OUT" | grep -q "401 Unauthorized" ||
  { echo "the screen did not carry the reason the session gave: $OUT"; exit 1; }
printf '%s\n' "$OUT" | grep -q "banner line 1$" &&
  { echo "the screen carried the front of the output; a CLI's reason is at the end, and this is what pushed it off"; exit 1; }
printf '%s\n' "$OUT" | grep -q "banner line 60$" ||
  { echo "the screen carried neither end of the output"; exit 1; }

# --- and it says what to type, out of the declaration -----------------------
printf '%s\n' "$OUT" | grep -qF "$LOGIN" ||
  { echo "the ladder named the rung and not the command that closes it — measured against the declaration, never against the real Codex CLI: $OUT"; exit 1; }
printf '%s\n' "$OUT" | grep -qF "agent-kit setup codex" ||
  { echo "the ladder did not name the walk that goes through the install and the login: $OUT"; exit 1; }

# And the kit ran neither of them. The shims write down every argv they are
# given, so a `login` line here is the kit logging somebody in — which it
# prints and never runs.
grep -q "^login" "$BENCH/codex-argv" &&
  { echo "the ladder ran the login command itself; it prints a login and runs nothing"; exit 1; }
exit 0
