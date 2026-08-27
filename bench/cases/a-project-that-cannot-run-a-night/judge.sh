#!/bin/sh
# The trap first: the declaration really does name a command, and this machine
# really cannot start it. Without both, the door agreeing costs nothing.
grep -q flibbertigibbet "$REPO/.agent-kit/v3/project.toml" ||
  { echo "the trap was not planted: nothing impossible is declared"; exit 1; }
command -v flibbertigibbet >/dev/null &&
  { echo "the trap was not planted: that command exists here"; exit 1; }

SAID=$($KIT -C "$REPO" next) || { echo "the door did not answer"; exit 1; }
FIRST=$(printf '%s\n' "$SAID" | head -1)
case "$FIRST" in
  no-such-command:*) ;;
  *) echo "the door answered ${FIRST%%:*} rather than no-such-command"; exit 1 ;;
esac
printf '%s\n' "$SAID" | grep -q flibbertigibbet ||
  { echo "the door did not name the word nothing can start"; exit 1; }
exit 0
