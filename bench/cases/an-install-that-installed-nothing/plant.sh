#!/bin/sh
set -e
mkdir -p "$BENCH/bin"

# claude, and it stays this way: nothing here ever installs it.
cat > "$BENCH/bin/claude" <<'SH'
#!/bin/sh
echo "claude: not installed on this machine" >&2
exit 127
SH
chmod +x "$BENCH/bin/claude"

# An installer that does its whole job by saying it did. It leaves a mark, and
# the mark is what proves this trap was standing when the judge ran: without it
# the judge would be green on a world where no install was even attempted.
cat > "$BENCH/bin/npm" <<'SH'
#!/bin/sh
printf '%s\n' "$@" >> "$BENCH/npm-argv"
exit 0
SH
chmod +x "$BENCH/bin/npm"
