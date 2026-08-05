# Developing the kit

## Repository layout

```text
.claude-plugin/marketplace.json   this repository is also the marketplace
plugins/agent-kit/                the plugin — everything that ships
  .claude-plugin/plugin.json      manifest; its `version` is what pins an install
  README.md                       the command list; the validator holds it to the skills
  skills/<name>/SKILL.md          one directory per command — this IS the behavior
  skills/<name>/references/       what one command needs on one step and not before
  rules/                          what several commands share: asking, pull requests, closing
  agents/                         the subagents a command may start
  scripts/                        check.py, orchestrate.py — what must not depend on remembering
  templates/knowledge/            the shape of each knowledge file blueprint writes
  templates/project.yml           the shape of a project's own corner
  templates/run.json              the shape of one run's memory; its field list is closed
  templates/technical_debt.md     the ledger, carrying its own format and rules in its header
scripts/                          validate.sh, release.sh, measure.py
docs/design/                      what was decided and why; kit-v1.md is the current one
```

The invariant: **behavior lives in exactly one file.** A skill that restates a rule instead of
pointing at it silently opts out of every later fix to that rule — which is how a fixed rule went on
being broken in two skills for a whole release. The same goes for the templates: they carry the
shape of a record so that no prompt has to describe it.

## Which file a piece of text belongs in

Three levels, and the level is chosen by **how often the text is needed** — never by how long it is:

| Needed | Where it goes | What it costs |
|---|---|---|
| on every step of every run | the command's own `SKILL.md` | the most: everything read is re-read on every step that follows |
| on one step, or by several commands | `rules/`, or the command's `references/` | one read, from that step to the end of the run |
| once in a project's life, or as a file is first written | `templates/` | one read, by the command that creates the file |

A fourth level would not help, and neither would splitting further inside these. Every hop costs a
tool call, gives the same rule one more place to be restated, and a rule that takes two links to
reach is a rule an agent decides without. Length is not a reason to move text down: an explanation
is what makes a rule executable, and a kit of laws without reasons is what version 0.17.0 died of.
Move a text down only when a run that does not do this thing never needs to read it at all.

## Who writes what, in a project

Every file the kit puts in somebody's repository, and everything allowed to write it. A new
mechanism that writes anywhere is checked against this table first — the rule *only `blueprint`
rewrites knowledge* was true when it was written and had quietly grown four writers by August,
because each was added on its own and nobody looked at the column.

| File | Who writes it | What they may write |
|---|---|---|
| `docs/knowledge/*.md` — prose | `blueprint` | all of it; nothing else touches the prose |
| `docs/knowledge/*.md` — an entry's `state:` line | `ship`, the closing session, and `next` via `check.py --sync` | `building (pr: n)` when a pull request opens; `built` or back to `planned` from a merged or closed one. Every run of the check says when a line is behind; only `--sync` moves it |
| `docs/knowledge/*.md` — `[assumed …]`, `[found …]` and `[stale …]` blocks | `ship`, `fix` | a block under the entry they stood in for; `blueprint` is what deletes one |
| `docs/technical_debt.md` | `ship`, `fix`, the closing session, and `blueprint` for a line whose work was prose | a line appended, or a finished line deleted; never a ticked box |
| `docs/audits/<lens>.md` | `audit` | the lens's own work list, rewritten whole on each run |
| `docs/audits/<lens>.md` — the boxes | the closing session, `next` | `- [x]` on an item verified as done, and nothing else in that commit |
| `.agent-kit/project.yml` | `blueprint` | all of it; no build command edits its own settings |
| `.agent-kit/runs/<slug>/run.json` | the run it belongs to, and the driver | the run writes its own state; the driver writes `step`, `blockers` and the batch's own file |
| `.agent-kit/runs/<slug>/run.log` | the driver | when a session started, stalled, waited out a limit, finished |

Two properties are worth keeping as the table grows: **one writer per kind of content**, even where
a file has several writers overall; and **nothing writes to a project as a side effect of reading
it** — that is why `check.py` moves a state line only when it is asked with `--sync`.

The lifecycle of each record — who records it, what raises it again, who may close it, and who
removes it — is [docs/design/the-loop.md](design/the-loop.md), which is the map the tables here, in
the plugin README, in `ship` and in `rules/pull-requests.md` all have to agree with.

## Every mechanism arrives with four answers

Who writes it, who reads it, **who may close it**, and what becomes impossible without it. No fourth
answer, no mechanism.

The third question is the one that was missing. Half the defects of the 5 August audit were records
with no writer or no reader; the ones found the day after were records nobody was allowed to remove
— a ledger line whose resolver could not delete it, a merged feature no command was permitted to
mark. A record with no closer is not a slow leak, it is a list that grows until it stops being read.

The kit is being rebuilt. Read [docs/design/kit-v1.md](design/kit-v1.md) before changing anything:
it records what was removed and why, and adding one of those things back needs an argument rather
than an oversight. Six commands work, `mvp` is a declared stub, and `scripts/validate.sh` enforces
that a command is either behavior or a stub marked as such in the plugin README.

## Adding a command

1. `plugins/agent-kit/skills/<name>/SKILL.md`, frontmatter first. `name` must match the directory,
   and `description` is how Claude Code decides to surface it — write it as what it does and when to
   use it. Add `disable-model-invocation: true` so it is only ever started deliberately.
2. Add the row to `plugins/agent-kit/README.md`, and drop the "not written yet" note.
3. Keep it short. Prose in a command is re-read on every step of every run, so rationale belongs
   here in `docs/design/`, not in the command.
4. `bash scripts/validate.sh`.

## Versioning

Semver from the perspective of a project that installed the kit. A command removed or renamed is a
breaking change; a command added is a minor. `1.0.0` is reserved for the release where every
command works — until then the rewrite ships as `0.x` so the version never claims more than exists.

`scripts/release.sh <version>` bumps `VERSION`, `plugin.json` and `marketplace.json` together,
validates, commits and tags. Publish with `git push && git push --tags`. A release that needs a
manual step on the user's side gets a note under `migrations/<version>.md`, referenced from the
changelog.

**The changelog goes in with the work, not with the release.** `release.sh` refuses to start on a
dirty tree and commits only the three version markers, so the section for the version being cut has
to be committed already — write it as the last edit of the work it describes.
