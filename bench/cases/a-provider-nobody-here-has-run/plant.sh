#!/bin/sh
set -e
# Nothing about the machine the bench runs on is assumed. The world inherits its
# PATH, so a real `npm` and even a real `codex` may be standing on it: an install
# command that reached the real `npm` would go to the network, and a real `codex`
# would be started with somebody's real account behind it.
mkdir -p "$BENCH/bin"

# What a working Codex looks like, by the reference this declaration was written
# from: it answers `--version`, and `exec` reads the prompt from stdin. It writes
# down every argv it is handed, which is how the judge shows the kit ran the
# commands it ran and no others.
cat > "$BENCH/codex-once-installed" <<'INNER'
#!/bin/sh
printf '%s\n' "$*" >> "$BENCH/codex-argv"
if [ "$1" = "--version" ]; then echo "codex-cli 0.55.0"; exit 0; fi
cat > /dev/null
echo 'looks fine from here'
INNER
chmod +x "$BENCH/codex-once-installed"

# And what it looks like before anybody installs it: on PATH, answering nothing.
cat > "$BENCH/bin/codex" <<'INNER'
#!/bin/sh
printf '%s\n' "$*" >> "$BENCH/codex-argv"
echo "codex: not installed on this machine" >&2
exit 127
INNER
chmod +x "$BENCH/bin/codex"

# `npm` is the first word of the command `codex` declares. This one writes down
# that it ran and puts the tool where the real one would.
cat > "$BENCH/bin/npm" <<'INNER'
#!/bin/sh
printf '%s\n' "$@" >> "$BENCH/npm-argv"
cp "$BENCH/codex-once-installed" "$BENCH/bin/codex"
INNER
chmod +x "$BENCH/bin/npm"
