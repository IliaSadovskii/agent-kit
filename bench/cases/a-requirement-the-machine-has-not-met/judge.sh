#!/bin/sh
# The walk is put to a machine of this case's own making: PATH is the case's
# own bin and nothing else, so what the server outside happens to carry cannot
# answer for it. The kit itself is reached by an absolute path, and `setup`
# runs no command at all — it asks PATH and prints.
ONLY="$BENCH/bin"

# --- what the provider declares, asked of the kit ---------------------------
# Never written down here: a judge that checks a string it wrote itself is
# measuring its own typing. `codex` is the shipped declaration that requires
# something; the day it stops, the two reads below come back empty and this
# case says so rather than going quietly green.
ASK="from agent_kit.providers.registry import facts"
INSTALL=$($PYTHON -c "$ASK; print(' '.join(facts('codex').install))") ||
  { echo "the kit could not say how codex is installed"; exit 1; }
NEEDS=$($PYTHON -c "$ASK; print(' '.join(one.binary for one in facts('codex').requires))") ||
  { echo "the kit could not say what codex needs standing first"; exit 1; }
[ -n "$INSTALL" ] || { echo "codex declares no install command"; exit 1; }
[ -n "$NEEDS" ] || { echo "codex declares nothing that has to be standing first"; exit 1; }
INSTALLER=${INSTALL%% *}

# --- the trap was standing --------------------------------------------------
# A judge that only checks what a screen said is green where the machine it was
# said about was never made. Both halves are shown first: the installer is here,
# and what the tool runs on is not.
[ -x "$ONLY/$INSTALLER" ] ||
  { echo "the trap was not planted: '$INSTALLER' is not in this case's own bin"; exit 1; }
for WORD in $NEEDS; do
  [ -e "$ONLY/$WORD" ] &&
    { echo "the trap was not planted: '$WORD' is standing in this case's own bin"; exit 1; }
done

SAID=$(PATH="$ONLY" $KIT setup codex </dev/null 2>&1)
CODE=$?
[ "$CODE" = "8" ] ||
  { echo "the walk exited $CODE where a stream with nobody behind it is 8: $SAID"; exit 1; }

# --- what was measured about each, and not one word for both ----------------
LINE_HAS=$(printf '%s\n' "$SAID" | grep -n "^ *ok  $INSTALLER  " | head -1 | cut -d: -f1)
[ -n "$LINE_HAS" ] ||
  { echo "the walk did not say it had found '$INSTALLER': $SAID"; exit 1; }
for WORD in $NEEDS; do
  LINE_WANTS=$(printf '%s\n' "$SAID" | grep -n "^ *no  $WORD  " | head -1 | cut -d: -f1)
  [ -n "$LINE_WANTS" ] ||
    { echo "the walk did not say '$WORD' is missing: $SAID"; exit 1; }
done

# --- above the command, which is the whole of the case ----------------------
# A requirement printed under the install command is a requirement read after
# it has been run, and the install is the thing it was supposed to stop.
LINE_CMD=$(printf '%s\n' "$SAID" | grep -nF "$INSTALL" | head -1 | cut -d: -f1)
[ -n "$LINE_CMD" ] ||
  { echo "the walk did not print the command the provider declares"; exit 1; }
[ "$LINE_WANTS" -lt "$LINE_CMD" ] ||
  { echo "the missing requirement stands at line $LINE_WANTS, under the command at $LINE_CMD"; exit 1; }
exit 0
