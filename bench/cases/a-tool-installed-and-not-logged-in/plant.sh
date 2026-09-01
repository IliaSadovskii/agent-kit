#!/bin/sh
set -e
# Nothing about the machine the bench runs on is assumed. The world inherits its
# PATH, so a real `codex` may be standing on it, and a real one would be started
# with somebody's real account behind it and would spend somebody's real quota.
mkdir -p "$BENCH/bin"

# What the owner's machine printed on 1 September 2026, word for word: the
# banner first, and the reason after all of it. The sixty lines between them are
# what makes the trim measurable — a screen that keeps the front of this shows
# `banner line 1` and never reaches the error at all.
cat > "$BENCH/codex-loggedout" <<'INNER'
#!/bin/sh
printf '%s\n' "$*" >> "$BENCH/codex-argv"
if [ "$1" = "--version" ]; then echo "codex-cli 0.144.6"; exit 0; fi
cat > /dev/null
echo "Reading prompt from stdin..." >&2
n=1
while [ "$n" -le 60 ]; do echo "banner line $n" >&2; n=$((n + 1)); done
echo "ERROR: unexpected status 401 Unauthorized: Missing bearer or basic authentication in header, url: https://api.openai.com/v1/responses" >&2
exit 1
INNER
chmod +x "$BENCH/codex-loggedout"

# And the same tool with an account behind it. Without this half the case could
# not tell "the rung fired" from "this command refuses whatever it is given" —
# and the rung under measurement is one that says `ok` on the other shape.
cat > "$BENCH/codex-working" <<'INNER'
#!/bin/sh
printf '%s\n' "$*" >> "$BENCH/codex-argv"
if [ "$1" = "--version" ]; then echo "codex-cli 0.144.6"; exit 0; fi
cat > /dev/null
echo "Reading prompt from stdin..." >&2
printf '```json\n{"branch": "kit/x", "can_write": true, "notes": []}\n```\n'
INNER
chmod +x "$BENCH/codex-working"

# On PATH as well, refusing everything: whatever this case gets wrong, it must
# not be able to reach a `codex` that belongs to somebody.
cat > "$BENCH/bin/codex" <<'INNER'
#!/bin/sh
printf '%s\n' "$*" >> "$BENCH/codex-argv"
echo "codex: this case never meant to run me" >&2
exit 127
INNER
chmod +x "$BENCH/bin/codex"
