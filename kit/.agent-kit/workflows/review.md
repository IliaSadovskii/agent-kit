# Review workflow

An adversarial, read-only review of work in progress — the current working-tree changes or the
branch diff against the default branch — outside the full feature pipeline.

Delegate to the `reviewer` role; its method lives there. Report the findings back by severity, each
with `file:line` and a one-line reason. `review` changes nothing itself; the user decides what to
act on.
