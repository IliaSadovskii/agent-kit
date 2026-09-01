#!/bin/sh
set -e
# The installer, and nothing else. What this case is about is the difference
# between the two: `npm` is standing here, and what the tool it installs would
# then run on is not — which is the machine the owner spent an afternoon on,
# finding out by conversation what the kit could have printed in a line.
#
# It is a script that does nothing. Nothing in this case ever runs it: the kit
# prints install commands and runs none, and the judge does not run this one
# either, so what is needed is a file PATH can find and mark as runnable.
mkdir -p "$BENCH/bin"
cat > "$BENCH/bin/npm" <<'INNER'
#!/bin/sh
echo "npm: this case never runs the install command" >&2
exit 1
INNER
chmod +x "$BENCH/bin/npm"
