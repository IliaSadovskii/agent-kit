#!/bin/sh
WALLED="$BENCH/cannot-write.md"
FREE="$BENCH/can-write.md"

# --- the trap was standing --------------------------------------------------
# The answer that must say no really says no, and the answer that must say yes
# really says yes. A judge that went straight to "it refused" would be green
# against a kit where `provider check fake` refuses for any reason at all.
[ -f "$WALLED" ] || { echo "the trap was not planted: no walled-in answer"; exit 1; }
[ -f "$FREE" ] || { echo "the trap was not planted: no control answer"; exit 1; }
grep -q '"can_write": false' "$WALLED" ||
  { echo "the trap was not planted: the walled-in answer does not say so"; exit 1; }
grep -q '"can_write": true' "$FREE" ||
  { echo "the trap was not planted: the control answer does not say so"; exit 1; }

# --- the control: the same command, and it earns a level --------------------
OUT=$($KIT provider check fake --option "reply=$FREE" 2>&1)
CODE=$?
[ "$CODE" = "0" ] ||
  { echo "the trap was not armed: the same command refuses even a session that can write ($CODE): $OUT"; exit 1; }
printf '%s\n' "$OUT" | grep -q "level A" ||
  { echo "the trap was not armed: a session that can write earned no level: $OUT"; exit 1; }

# --- and the one that cannot write earns nothing ----------------------------
OUT=$($KIT provider check fake --option "reply=$WALLED" 2>&1)
CODE=$?
[ "$CODE" = "4" ] ||
  { echo "the ladder exited $CODE where a provider that earned no level is 4: $OUT"; exit 1; }
# The code, and the rung by name. Never the prose around them: a sentence gets
# rewritten and the case starts measuring somebody's wording.
printf '%s\n' "$OUT" | grep -q "provider-not-ready" ||
  { echo "the ladder did not refuse by name"; exit 1; }
printf '%s\n' "$OUT" | grep -qF 'the rung `writes`' ||
  { echo "the ladder stopped somewhere other than the rung about writing: $OUT"; exit 1; }
exit 0
