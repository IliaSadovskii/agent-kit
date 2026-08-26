## What you never do to this repository

Three things, whatever role you are in and whatever the task seems to need:

- **Never merge a pull request.** Not `gh pr merge`, not the button, not a merge commit
  of your own. The kit opens pull requests and never closes them: the decision to release
  is the owner's, and it is the only thing they get to make about a night's work.
- **Never push to the trunk.** Work goes to the branch the head of this input names, and
  reaches the trunk through a pull request or not at all.
- **Never force a push, and never delete a remote branch.** A push that drops commits
  already on the remote destroys work nobody can get back.

A git hook refuses the last two, so the ordinary command will simply fail. It cannot see
the first one — `gh pr merge` is an API call, not a push — and `--no-verify` walks past
all of it. So these are not obstacles to work around: they are the rule, and going round
the hook is the same defect as merging.
