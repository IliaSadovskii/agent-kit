#!/bin/sh
# The trap first: what was planted is still there, and git still does not know it.
test -f "$REPO/.agent-kit/v3/trees/two/something" ||
  { echo "what was planted in the way is gone, so nothing was in the way"; exit 1; }
git -C "$REPO" worktree list | grep -q 'trees/two' &&
  { echo "the planted directory became a worktree; nothing was refused"; exit 1; }

# The feature that could not be started says what stopped it, by the code.
grep -q 'tree-in-the-way' "$BATCH_FILE" ||
  { echo "the feature that could not be started does not name what stopped it"; exit 1; }

# And the child that was already building is accounted for: its pull request is
# in the record, and its branch is not something only the orphan knows about.
grep -q 'pull/7' "$BATCH_FILE" ||
  { echo "the child that was already building is not in the record"; exit 1; }
test "$(git -C "$REPO" rev-list --count main..kit/one)" -ge 1 ||
  { echo "the feature that was building never landed"; exit 1; }
exit 0
