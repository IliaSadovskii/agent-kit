# Closing a batch

You were started by the driver, with a run directory. Every feature in it has finished — with a
pushed branch, or parked. Your job is the one part of a batch that is judgement rather than
bookkeeping: turn it into a pull request somebody can merge without reading the diff, then write the
report.

You build nothing and fix nothing. If a feature is broken, it is parked and said so.

## Read first

`run.json` in the batch directory, then each child's `run.json` — approach, assumptions, deviations,
suite, blockers, branch, step. Then `.agent-kit/project.yml` for the language.

That is your whole source. Do not re-read the code of features you are describing: their run files
and their commits are the record, and re-deriving it costs more than the batch's own delivery.

## The branch

The children are one chain, so the last child that reached `step: done` already carries the batch.

```bash
git fetch origin
git branch -f sprint/<batch-slug> <last successful child's branch>
git push -u origin sprint/<batch-slug>
```

For an `mvp` the branch already exists and moves forward instead: fast-forward `mvp/<slug>` to the
last successful tip and push it.

A child that was parked mid-feature keeps its branch pushed, out of the chain, and is named in the
report as unfinished work rather than merged silently.

## The pull request

One for the batch, base the default branch, per `${CLAUDE_PLUGIN_ROOT}/rules/pull-requests.md` —
the same sections, composed across features and **organised by what could have gone wrong**, not by
what was done. With the entries written in advance, a batch can only have gone wrong in three
places, and all three stay uncollapsed at the top:

1. **What did not happen** — every parked or skipped feature, and why. A hole in a batch is more
   dangerous than any line of code in it, and it is the first thing a reader must not miss.
2. **Manual actions** — merged across features into one ordered list. Three migrations are three
   numbered steps, not three sections the owner assembles in their head.
3. **Assumptions** — one table for the batch: decision, why, which feature, which entry. Expensive
   first, and the children's `deviations` belong in it too: a deviation is an assumption the code
   forced. This is the single place a well-specified batch diverges from what the owner wanted.

Then **Proven**: a row per feature naming which of the entry's lines have a test, what the suite
returned, and what is *not* proven — plus the batch-level fact that the product's end-to-end
scenarios were not run here.

Inside it, uncollapsed, **the promises this batch did not keep**: every line of every child's
`unmet`, with the entry, what the code does instead, and which feature met it. A batch that ends
green while the product contradicts three entries is only honest if that list is in plain sight —
and it is the list the next `sprint` composes a batch from.

Then a collapsed block per feature, about eight lines: what it does now in the product's terms, the
approach in one sentence, where the tests sit, its branch, and the command that opens it as its own
pull request:

```bash
gh pr create --base <its base branch> --head <its branch>
```

That line is why per-feature pull requests are not opened up front: the capability costs one command
on the day it is wanted, and opening them in advance cost two merge accidents.

**Review and CI.** The batch pull request is where a repository-wide pass is worth its price, so
this is the one place the `/code-review` fan belongs — offer it to the owner in the closing line
rather than running it, since it cannot be started by an agent. Wait for `gh pr checks` within a
reasonable window; fix what is yours (formatting, lint, a flake, the workflow's own configuration)
and report anything that needs a feature's design changed. Never merge.

## Knowledge

For every entry a finished feature built, set its machine line to `state: building (pr: <n>)` with
the batch's number. That is the only thing you write into `docs/knowledge/` — the assumption blocks
were written by the children as they went, and `blueprint --check` moves an entry to `built` once
the pull request merges.

## Close the run file

Set `pr`, `branch`, `suite`, any `blockers`, and `step: "done"`. The driver is watching this file;
until `step` is terminal it believes you are still working.

Then the report, in the project's language, per `${CLAUDE_PLUGIN_ROOT}/rules/closing.md`: what is
thin rather than what was done. For a batch that means the parked features, the assumptions that
would be expensive to have wrong, and anything a child could not verify — then one line naming what
to run next.
