#!/bin/sh
set -e
# Two answers to one question, and the pair is the trap: the same command, the
# same provider, the same contract kept — and one of them says the session could
# not write. Without the second file this case could not tell "the rung fired"
# from "this command always fails".
cat > "$BENCH/cannot-write.md" <<'INNER'
```json
{"branch": "kit/x", "can_write": false, "notes": ["a read-only sandbox"]}
```
INNER

cat > "$BENCH/can-write.md" <<'INNER'
```json
{"branch": "kit/x", "can_write": true, "notes": []}
```
INNER
