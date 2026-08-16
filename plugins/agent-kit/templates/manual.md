# Manual actions

What only the owner can do: a secret to place, an account to open somewhere, a device to hold, a
production environment to fill in. Written by the runs, read before every command, closed by the
owner doing the work — or by the program, which is the point of this file.

Until 2.19.0 these lived in `.agent-kit/runs/<slug>/run.json`, which is git-ignored and dies with
the machine, and reached the owner only through a pull request's **Manual actions** section. That
section is still where they meet them; this file is what remembers them the day after the merge,
when the pull request is closed and nobody opens it again.

**Nothing a script can do belongs here.** A migration to apply, a build argument, a port, a file
mode: those go into `commands.run`, and a run that did one by hand folds it in there and says so. A
setting that already works is an assumption, not an action. Measured on one run, a list of nineteen
held six that genuinely needed a person — five were things a script should have done and four were
settings that were fine — and it was the thirteen that made the six unfindable.

One line per action, newest first, with its proof on the line under it:

```markdown
- [ ] <what to do> — <where> · <before_run | before_merge | before_release> · PR #<n>
      proof: `<a command that exits 0 once this is done>`
```

## The proof is a command, and that is what closes the line

`proof` is not a sentence about how the owner will know it worked. It is a command that **exits 0
once the action has been done and non-zero until then** — the key is readable in the environment,
the migration is applied, the endpoint answers. Then nobody has to remember to tick anything:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py" . --manual
```

runs every proof and deletes the lines that pass. A list that empties itself is a list that is still
true a month later, which no list closed by hand has ever been.

**A proof only ever reads.** It must not migrate, deploy, write a file or call anything that costs
money — it is run unattended, by a program, and possibly many times. A command that changes the
world is the action itself and belongs above the line, not below it.

**Where no command can answer, write it plainly:**

```markdown
      proof: none — only a person can see that the store listing went live
```

That line is honest and it is rare. Everything with `proof: none` stays until the owner deletes it,
and a file where most lines say `none` is a file whose actions were written the lazy way — the
count is what tells you, and the check says it.

## When it is due

`before_run` — the product will not start without it. `before_merge` — before this lands.
`before_release` — before it ships.

**`stage` in `.agent-kit/project.yml` decides which of those anyone is shown.** On a project at
`development` there is no release, so `before_release` lines are not work anybody is going to do this
week: they are kept and not printed. A push credential for an app nobody has published is not a task,
and on one measured run that group was a third of a list of nineteen.

## Who writes here

A run records the action in its own `run.json` → `manual` as it finds it, because that is what the
pull request's section is composed from. The session that closes the batch copies them into this
file in the same commit as the ledger — one movement, both records, and the reasoning stays in the
pull request the line names.

A run that delivers its own pull request writes here itself, at the same point.

Nothing else edits this file. It is not a place for notes, for a task the owner asked for, or for
work a run decided to skip — that last one is `docs/technical_debt.md`, and the two are different
records with different closers.

Keep it in the project's language, like everything else the owner reads.

```markdown
- [ ] put the Stripe live key in the deployment environment as `STRIPE_SECRET_KEY` — the payments
      service reads it at boot · before_release · PR #21
      proof: `test -n "$STRIPE_SECRET_KEY"`
- [ ] create the moderation account in the admin panel and confirm its email — nothing can be
      reviewed until one exists · before_run · PR #21
      proof: `php artisan tinker --execute="exit(User::where('role','moderator')->exists() ? 0 : 1);"`
```

Delete this file's own prose once the first real action is in it, or keep it — the check counts only
open boxes outside a fenced block, so the two above are not counted.
