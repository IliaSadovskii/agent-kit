# The trap first: the manifest really is gone, from the working copy and from
# the commit the audit would have measured.
test ! -f "$REPO/pyproject.toml" || { echo "the manifest is still here"; exit 1; }
git -C "$REPO" cat-file -e HEAD:pyproject.toml 2>/dev/null && { echo "the manifest is still in the commit"; exit 1; }

# Then the mechanism: refused before anything was spent. No room, so no
# inventory and no attempt.
set -- "$AUDITS"/dependencies-*
test ! -d "$1" || { echo "a room was made for an audit that was refused: $1"; exit 1; }
exit 0
