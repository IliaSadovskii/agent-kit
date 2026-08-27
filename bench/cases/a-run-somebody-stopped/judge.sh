#!/bin/sh
# The trap first: the stopped run really is stopped, and its record really
# carries the reason the door is supposed to print.
grep -q '"status": "stopped"' "$REPO/.agent-kit/v3/runs/rates/run.json" ||
  { echo "the trap was not planted: no run was stopped"; exit 1; }
grep -q "the owner wanted the rates checked first" "$REPO/.agent-kit/v3/runs/rates/run.json" ||
  { echo "the trap was not planted: the stop wrote down no reason"; exit 1; }

SAID=$($KIT -C "$REPO" next) || { echo "the door did not answer"; exit 1; }
FIRST=$(printf '%s\n' "$SAID" | head -1)
case "$FIRST" in
  run-stopped:*rates*) ;;
  *) echo "the door answered $FIRST rather than run-stopped about rates"; exit 1 ;;
esac
printf '%s\n' "$SAID" | grep -q "agent-kit run reopen rates" ||
  { echo "the door named no way to carry the stopped run on"; exit 1; }
printf '%s\n' "$SAID" | grep -q "the owner wanted the rates checked first" ||
  { echo "the door did not say why it stopped"; exit 1; }
exit 0
