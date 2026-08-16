# Developing the kit

## Repository layout

```text
.claude-plugin/marketplace.json   this repository is also the marketplace
plugins/agent-kit/                the plugin — everything that ships
  .claude-plugin/plugin.json      manifest; its `version` is what pins an install
  README.md                       the command list; the validator holds it to the skills
  skills/<name>/SKILL.md          one directory per command — this IS the behavior
  skills/<name>/references/       what one command needs on one step and not before
  rules/                          what more than one command shares: asking, pull requests,
                                  closing, preflight, channels, knowledge writing — and craft,
                                  which the two commands that write product code and the reviewer
                                  that judges it all read
  agents/                         the subagents a command may start
  hooks/                          the one guard: what no run may do, enforced outside the model
  scripts/                        check.py, orchestrate.py — what must not depend on remembering
  templates/knowledge/            the shape of each knowledge file blueprint writes
  templates/project.yml           the shape of a project's own corner
  templates/run.json              the shape of one run's memory; its field list is closed
  templates/batch.json            the shape of what a batch leaves in the repository, and all of
                                  a batch that outlives the machine it ran on
  templates/technical_debt.md     the ledger, carrying its own format and rules in its header
scripts/                          validate.sh, release.sh, measure.py
docs/design/                      what was decided and why; kit-v1.md is the current one
docs/planned.md                   what is planned next — and, in its second half, what was
                                  proposed, checked against the payload and refused, with the
                                  reason. Read that half before proposing anything
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

That table moved to [docs/design/the-loop.md](design/the-loop.md), beside the record it belongs to.
It was written here as *per file, who may write it* and there as *per record, who may close it* —
two views of one graph, for the same reader at the same moment, and two places for it to disagree
with itself.

## Every mechanism arrives with four answers

Who writes it, who reads it, **who may close it**, and what becomes impossible without it. No fourth
answer, no mechanism.

The third question is the one that was missing. Half the defects of the 5 August audit were records
with no writer or no reader; the ones found the day after were records nobody was allowed to remove
— a ledger line whose resolver could not delete it, a merged feature no command was permitted to
mark. A record with no closer is not a slow leak, it is a list that grows until it stops being read.

**And a rule is a mechanism.** Its closer went unwritten for as long as the third question did, and
the answer differs by home: a rule in a program is closed by deleting the check and its test in one
commit, and a rule in prose is closed by a design note that retires it. Nothing else may remove
either — "it looked stale" is how a rule that was paid for in a defect goes back out of the payload.

## A check that does not understand its input says so

Silence means *nothing is wrong*. A check that also goes quiet when it cannot read what it was
given makes those two indistinguishable, and the one it is really reporting is the second — which
is worse than having no check at all, because the run believes it is covered.

Twice in two days:

- `--offline` was given to `next` so it would stop writing, and it also stopped `gh` being asked
  anything — so three rungs of its ladder, all of them about open pull requests, silently never
  fired again. The flag did what it said; nothing said what it cost.
- five runs wrote `review.findings` as sentences, and the closing check skipped every item it could
  not read as a record. The rule about not finishing with an open critical finding was never applied
  once, and reported nothing at all.

So: when a program of this kit meets input it cannot judge, it **names it and takes it as unjudged**
— never as clean. Do not guess the meaning out of prose either: a value guessed at is a value nobody
can be held to, and salvaging it teaches the next run that the shape was optional.

The kit is being rebuilt. Read [docs/design/kit-v1.md](design/kit-v1.md) before changing anything:
it records what was removed and why, and adding one of those things back needs an argument rather
than an oversight. Six commands work, `epic` is a declared stub, and `scripts/validate.sh` enforces
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
