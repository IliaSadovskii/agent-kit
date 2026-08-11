# Closing a batch

You were started by the driver, with a run directory. Every feature in it has finished — with a
pushed branch, or parked. Your job is the one part of a batch that is judgement rather than
bookkeeping: turn it into a pull request somebody can merge without reading the diff, then write the
report.

You build nothing and fix nothing. If a feature is broken, it is parked and said so.

## Read first

`run.json` in the batch directory, then each child's `run.json` — approach, assumptions, deviations,
`review`, `answers`, `unmet`, `deferred`, `closed_debt`, suite, blockers, branch, step, and whatever
a child left in `notes`. Then `.agent-kit/project.yml` for the language.

That is your whole source. Do not re-read the code of features you are describing: their run files
and their commits are the record, and re-deriving it costs more than the batch's own delivery.

## The branch

The children are one chain, so the last child that reached `step: done` already carries the batch.

```bash
git fetch origin
git branch -f sprint/<batch-slug> <last successful child's branch>
git push -u origin sprint/<batch-slug>
```

**Inside an `epic` the branch already exists and moves forward instead**: fast-forward `epic/<slug>`
to the last successful tip and push it. There is one pull request for that whole run, so the first
batch opens it and every batch after **rewrites its body and adds a comment with its own digest** —
what this batch built, what it proved, what it decided without the owner. They read one place and
see what is new since they last looked.

Say once, in the body, how to look at it without breaking the run:

```bash
git worktree add /tmp/<slug>-preview epic/<slug>
```

A `git checkout` in the project's own directory pulls the working tree out from under the children
still building in it. This line is what stops that at three in the morning; name a free port too if
the project already has an instance running.

A child that was parked mid-feature keeps its branch pushed, out of the chain, and is named in the
report as unfinished work rather than merged silently.

**A parked child built from a `task` rather than an entry also gets a line in the ledger** — what it
was for, how far it got, and its branch. An entry that was not built stays `planned` and the next
command sees it; a task has no such line anywhere, so without this the only work in the kit with no
home in the knowledge is also the only work that disappears the day this pull request merges.

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

**The ledger moves both ways in one commit.** Delete the lines the children finished — their
`closed_debt` — and write in the batch's leftovers, every child's `deferred`, one line each, newest
first, copying `${CLAUDE_PLUGIN_ROOT}/templates/technical_debt.md` if it is not there yet. Commit
it on the batch's branch, before the pull request, and say the movement in one line of the report:
nine items, three closed, two added. This is the only step of yours that leaves something behind in
the repository, and it is the difference between work the project remembers and work that lived in a
pull request until it was merged.

A child that says it closed an item whose line is still there did not finish it — carry the line
over untouched and name the feature in the report, rather than deleting on its word.

**Tick what the batch closed in the audits' work lists too**, when it was composed from one:
`- [x] закрыто PR #<n>` on each item its features finished, in `docs/audits/<lens>.md`, in the same
commit. Only three things ever tick them — this step, `next` and `accept`, each
only when it has verified an item is done — and the lens itself rewrites that file only on its next run, which may be months out. Until
then every command reads the list as though the work were still waiting.
Untouched items stay untouched: a box ticked on a guess costs more than one left open.

Then a collapsed block per feature, about eight lines: what it does now in the product's terms, the
approach in one sentence, where the tests sit, its branch, and the command that opens it as its own
pull request:

```bash
gh pr create --base <its base branch> --head <its branch>
```

That line is why per-feature pull requests are not opened up front: the capability costs one command
on the day it is wanted, and opening them in advance cost two merge accidents.

The **Review** section is composed from the children's `review` fields, not from their prose: the
verdict, then the findings that were closed and how, then any that were not — a finding a child
carried to the end without closing is the batch's most important line, and paraphrase is how it gets
lost. The same for **Assumptions**, whose owner-answered forks come from `answers` word for word.

**Review and CI.** Whether a repository-wide `/code-review` belongs on this pull request is settled
in `${CLAUDE_PLUGIN_ROOT}/rules/pull-requests.md`, and nowhere else — a batch offers it in its
closing line and never runs it; a batch inside an `epic` does not offer it at all.

Wait for `gh pr checks` within a reasonable window; fix what is yours (formatting, lint, a flake, the workflow's own configuration)
and report anything that needs a feature's design changed. Never merge.

## Knowledge

For every entry a finished feature built, set its machine line to `state: building (pr: <n>)` with
the batch's number. `blueprint --check` moves an entry to `built` once the pull request merges.

**Then apply the `[stale …]` blocks the children left.** A block says two things — what the entry
still claims, and what became true when the feature shipped — so putting the second in place of the
first is transcription, not judgement, and you are the last session that knows this batch. Delete
the block in the same commit and **name every sentence you changed in the report**, one line each,
uncollapsed: a pull request that edits the description it is judged against has to make that the
easiest thing in it to see.

Two limits, and outside them the block stays and travels to `blueprint`:

- **only what the block itself states.** If applying it means deciding anything the block does not
  already say, it is not yours.
- **never what an entry requires.** A block claiming the product should do something else is a
  product decision wearing a correction's clothes. The owner settles those.

`[assumed …]` blocks are not touched. They are questions nobody has answered, they are already in
the Assumptions section of this pull request, and answering them is the owner's.

## The one thing this batch leaves in the repository

`.agent-kit/runs/` is working state and is in the project's `.gitignore`, so every run file, every
driver log and everything a child left in `notes` lives on one machine and dies with it. What
survives a batch today is the pull request's prose — which no program can read, and which nobody can
read either once it has been rewritten eleven times by an `epic`.

So write **`docs/runs/<batch slug>.json`**, in the same commit as the ledger, and keep it small — a
few kilobytes, records rather than sentences:

```json
{ "slug": "2026-08-05-offers", "command": "sprint", "pr": 21, "branch": "sprint/2026-08-05-offers",
  "entries": ["developer.create_offer"], "children": 4, "spent": { "hours": 6.2, "features": 4, "sessions": 9 },
  "suite": "make test → 0, 118 passed", "assumptions": 3, "unmet": 1, "debt": { "closed": 2, "added": 3 },
  "review": { "findings": 37, "open": 0 }, "blocked": [] }
```

Counts, not copies: what each of those *says* is already in the pull request and in the knowledge,
and duplicating it here would give one fact two places to disagree with itself. `spent` is copied
from the run file as the driver left it — the only measurement of what a run costs that outlives the
machine it ran on, and the only thing a later gate can price a scope from.

**Who may remove one:** nobody, and that is deliberate — it is history, one file per batch, and it
is the smallest durable record the kit has.

## Close the run file

Set `pr`, `branch`, `suite`, any `blockers`, and `step: "done"`. The driver is watching this file;
until `step` is terminal it believes you are still working.

Then the report, in the project's language, per `${CLAUDE_PLUGIN_ROOT}/rules/closing.md`: what is
thin rather than what was done. For a batch that means the parked features, the assumptions that
would be expensive to have wrong, and anything a child could not verify — then one line naming what
to run next.
