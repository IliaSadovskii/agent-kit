# Working on this kit

This file is loaded into every session that works here, which is the only reason it exists: the
rules below were each learned by shipping a defect, and each was written down in
[docs/developing.md](docs/developing.md) — where nobody reads them unless they already suspect they
need to.

Read that file before a change of any size. This is the short form.

## Before adding a rule, choose its home

A rule lands in a command's `SKILL.md` by default, because prose is the only place with no barrier
to entry. Prose is the **last** choice, not the first. Four homes, in order of preference:

1. **A program.** Anything checkable mechanically stops being a thing to remember: the run calls the
   check and reacts to what it says. **Which** program follows the thing being judged — a rule about
   the project's own files belongs in `scripts/check.py`, a rule about a run file in the module that
   owns run files, a rule about the kit itself in `scripts/validate.sh`, which already enforces six
   of them and was never on this list. Naming one file here is how that file reached 2500 lines: it
   became the default address for everything mechanical, whatever it was about.
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

**A rule is a mechanism too, and its third answer was never written down.** A rule that lives in a
program is closed by deleting the check and its test, in one commit. A rule that lives in prose is
closed by a design note that says so — not by whoever noticed it and felt it was stale. Without that
line, prose rules only ever accumulate.

## A check that cannot read its input says so

Silence has to mean *nothing is wrong* and nothing else. A check that also goes quiet on input it
cannot parse makes those two indistinguishable — and it has happened three times: `--offline`
blinding `next` to pull requests, findings written as prose skipping the closing check, and a
storefront check that compared two empty lists and passed for months.

Never guess a value out of prose either. A guessed value holds nobody to anything.

## The size of `ship` is not the metric

Its whole reading set is ~50k characters against a run that costs ~15M tokens. What is worth
watching is **how many norms a run must hold at once at its hottest fork** — that is what killed
0.17.0, and it is not measured in bytes.

The outside work says the same thing. IFScale and ManyIFEval measure instruction-following against
the **number** of instructions; nothing measures it against bytes. The two numbers this kit has been
quoting are unfounded and are kept only as smoke alarms: Anthropic's *500 lines of `SKILL.md`* is
published without a justification, and the 12k-token ceiling was proposed by a model and agreed to
without a measurement. Neither is a rule to act on.

**Splitting a file a model reads is not the tool** — and only those. The whole argument is that a
*reference* may go unread, which is a fact about a model deciding whether to open a file, and says
nothing about Python, where an import is executed and cannot be declined. Half this repository is
Python; read generally, this rule has argued against every module the code half needs. Anthropic
warns that a referenced file may go unread, and this kit already rejected splitting `blueprint`'s
interview for that reason. Two moves are safe and both are in the four homes above: a rule that
moves **into a program** stops being held at all, and a rule that moves **to its only reader** is
not a split — the one who reads it reads it every time.
That is why the batch chapters left `rules/pull-requests.md`: no feature ever opens a batch's pull
request. Measured while doing it, in
[docs/design/2026-08-11-review.md](docs/design/2026-08-11-review.md).

## Conventions

- The payload is in English — prose, code, commit messages. What a project's owner reads is written
  in that project's language.
- `bash scripts/validate.sh` before any release, and it is what CI runs.
- The changelog goes in with the work; `scripts/release.sh <version>` only bumps and tags.
- Design decisions belong in `docs/design/`, not in a command. A command carries the rule and the
  reason it is executable; the argument for it lives in the design note.
