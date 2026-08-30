#!/bin/sh
CONFIG="$BENCH/home/.config/agent-kit/config.toml"

# --- the trap was standing --------------------------------------------------
[ -f "$CONFIG" ] || { echo "the trap was not planted: there is no configuration at all"; exit 1; }
grep -q "provider" "$CONFIG" &&
  { echo "the trap was not planted: this machine still names a provider"; exit 1; }

SAID=$($KIT -C "$REPO" next) || { echo "the door did not answer"; exit 1; }
FIRST=$(printf '%s\n' "$SAID" | head -1)
case "$FIRST" in
  no-provider*) ;;
  *) echo "the door answered ${FIRST%%:*} on a machine that can start nothing"; exit 1 ;;
esac
printf '%s\n' "$SAID" | grep -q "agent-kit setup" ||
  { echo "the door named no way in"; exit 1; }
exit 0
