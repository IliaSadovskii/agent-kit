# The manifest goes, and it goes in a commit: an audit measures what is
# committed, so deleting the file and leaving it in HEAD would measure nothing.
rm -f pyproject.toml
git add -A
git commit -qm "a project this lens has nothing to read"
