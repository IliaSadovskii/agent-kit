# Working on this kit

This file is loaded into every session that works here, which is the only reason it exists: the
rules below were each learned by shipping a defect, and each was written down in
[docs/developing.md](docs/developing.md) — where nobody reads them unless they already suspect they
need to.

Read that file before a change of any size. This is the short form.

## Before adding a rule, choose its home

A rule lands in a command's `SKILL.md` by default, because prose is the only place with no barrier
to entry. Prose is the **last** choice, not the first. Four homes, in order of preference:

1. **A program** — `scripts/check.py`. Anything checkable mechanically stops being a thing to
   remember: the run calls the check and reacts to what it says.
2. **A template** — `templates/`. The shape of a record lives in the file being written, and is read
   by whoever writes one, once.
3. **The reviewer** — `agents/reviewer.md`. A rule that is checked *on the result* can live entirely
   with the pass that checks it. Its context costs the run nothing.
4. **A shared rule** — `rules/`. Anything two commands both need. If it is in two `SKILL.md` files,
   it is already wrong.

Only what a run must hold *while deciding* belongs in the command itself.

## Every mechanism arrives with four answers

Who writes it. Who reads it. **Who may close it, and where that happens.** What becomes impossible
without it.

No fourth answer, no mechanism. Records with no writer or no reader cost this kit a release; records
nobody was allowed to remove cost it another.

## A check that cannot read its input says so

Silence has to mean *nothing is wrong* and nothing else. A check that also goes quiet on input it
cannot parse makes those two indistinguishable — and it has happened three times: `--offline`
blinding `next` to pull requests, findings written as prose skipping the closing check, and a
storefront check that compared two empty lists and passed for months.

Never guess a value out of prose either. A guessed value holds nobody to anything.

## The size of `ship` is not the metric

Its whole reading set is ~9k tokens against a run that costs ~15M. What is worth watching is **how
many mechanisms a run must hold at once** — that is what killed 0.17.0, and it is not measured in
bytes. The ceiling in [docs/design/2026-08-05-audit.md](docs/design/2026-08-05-audit.md) still
stands: past ~12k tokens, delete a mechanism rather than trimming an explanation.

## Conventions

- The payload is in English — prose, code, commit messages. What a project's owner reads is written
  in that project's language.
- `bash scripts/validate.sh` before any release, and it is what CI runs.
- The changelog goes in with the work; `scripts/release.sh <version>` only bumps and tags.
- Design decisions belong in `docs/design/`, not in a command. A command carries the rule and the
  reason it is executable; the argument for it lives in the design note.
