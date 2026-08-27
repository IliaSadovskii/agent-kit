# The trap first, twice over. The session really ran and really wrote — and it
# stood somewhere with no repository, which is what makes the answer below a
# removed possibility rather than a tidy-up afterwards.
test -f "$BENCH/the-session-ran" || { echo "the session never ran, so nothing was tried"; exit 1; }
grep -q "no repository here" "$BENCH/the-session-saw" || {
  echo "the session stood in a git repository: $(cat "$BENCH/the-session-saw")"; exit 1; }

# Then the mechanism: the working copy is exactly as it was.
test -z "$(git -C "$REPO" status --porcelain)" || { echo "the working copy moved"; exit 1; }
test ! -f "$REPO/oops.txt" || { echo "the session's file reached the project"; exit 1; }
grep -q RATE "$REPO/money.py" && { echo "the session's edit reached the project"; exit 1; }

# And an empty status does not tell a removed possibility from a moved one: a
# worktree whose directory was deleted leaves exactly the same status. So the
# refs and the history are counted too.
test "$(git -C "$REPO" for-each-ref --format='%(refname)' refs/heads)" = "refs/heads/main" || {
  echo "a branch appeared: $(git -C "$REPO" for-each-ref --format='%(refname)' refs/heads)"; exit 1; }
test "$(git -C "$REPO" rev-list --all --count)" = "1" || { echo "a commit appeared"; exit 1; }
exit 0
