# How a command ends

Every command in the kit ends the same two ways, whatever it did.

## Say where it is thin, not what you did

The owner can read the files and the pull request. A summary of the work adds nothing they cannot
see, and it sounds equally confident whether the work under it was thorough or shallow — which is
exactly the thing they are trying to judge.

So end with what only you know: what you could not settle, what you assumed, what you left alone,
and where the result is weaker than it looks. A command that names its own soft spots is one whose
confident parts can be trusted; a clean summary teaches the owner to check everything or nothing.

**Say where each of those now lives, and never hand it over.** *Your call*, *this is on you*, *needs
your decision* — every one of them turns a record into a chore, and a run that ends with three
chores teaches the owner that finishing a command means starting work. An assumption is under its
entry, a promise the product does not keep is marked on its test, work understood and not done is a
line in `docs/technical_debt.md`; each is printed by the check before the next command and offered
by `sprint` with no theme. Say that, in those words. The only thing that may be asked of the owner
is what genuinely needs their hands or their access — a secret, a migration, an account — and that
belongs in the pull request under Manual actions, not in a closing line.

## Then name the next command

One line, last, with the command already filled in and the reason in a clause:

```
дальше: /agent-kit:audit тесты — 50 записей помечены built, ни одна не проверена
дальше: смержи #42, потом /agent-kit:ship guest.report_post — следующее непостроенное в границах MVP
```

One recommendation, not a menu — a list of options hands the decision back to the owner along with
the work of making it. If the honest next step is that nothing needs doing, say that instead.

**Name what follows from the work you just did — and nothing else.** A pull request to merge, a
blocker to look at, the feature that was next in the batch: you know those, and nothing else in the
kit does. What you do not know is the rest of the project. You have not looked at the branches, the
pipeline or the audits since you started, and a recommendation to build the next entry while the
default branch is red is worse than no recommendation at all.

So when nothing follows from your own work, **name `/agent-kit:next`** — that is the command that
reads the whole state and ranks it, and it is a better answer than one invented to fill the line:

```
дальше: /agent-kit:next — по этой фиче всё закрыто, а что дальше по проекту, отсюда не видно
```

Written in the project's language, like everything else the owner reads.
