# What the structure review changed, 17 August 2026

The owner asked a question this kit had never been asked: not *does it work*, but **is it built
well** — file structure, separation of entities, whether the parts talk through interfaces they
never step outside of. Six releases came out of the answer, 2.19.4 through 2.20.4, and three
paragraphs of `CLAUDE.md` were rewritten. The argument belongs here, because a command carries the
rule and this page carries the reason.

Four independent readings were taken: one by the session doing the work, two by agents given the
same question and no access to each other, and one adversarial pass over the day's own diff. Every
number below was measured against three live projects — `beeplish`, `metsomeone`, `realest` — and
their 132 run files.

## What was actually wrong

Not size, and not the things that look wrong in a listing. `check.py` at 2500 lines was named as
the problem by two readings and was the problem in neither: it is already cut into five sections,
and its seams are visible on the CLI. What was wrong was **structural in the strict sense — one
fact held in several places, and no program holding them together**:

- terminal steps declared five times, the read-a-run-file loop written five times, `project_root`
  three times, `default_branch` twice **with different answers**, `project.yml` parsed twice;
- what kind of run a file describes — feature, errand, batch, epic — inferred in eight places from
  eight different signals;
- thirteen markdown formats written with prose in one file and read with a pattern in another, with
  nothing binding the two;
- lens names stated three times per command, agreeing by luck;
- `--offline` threaded through seven signatures, and each caller separately remembering what to
  answer when a question could not be asked. They remembered differently.

The last of those is the shape of every expensive defect this kit has had: **silence that means two
things**. Its own doctrine has said so for months; the day's finding is that the doctrine was being
broken inside the very functions written to enforce it.

## What the doctrine got wrong about itself

Two edits, and both were pressure the kit was applying to itself.

**"A program — `scripts/check.py`"** named one file as the home for every mechanical rule. That is
how a file becomes 2500 lines: it was the default address for anything checkable, whatever the rule
was about. It now says *a program*, with the program chosen by what is being judged — and
`scripts/validate.sh`, which had enforced six architectural rules since long before this page, was
never on the list at all.

**"Splitting a file is not the tool"** was written about files a model reads, where the argument is
real: a reference may go unread. Read generally — and half this repository is Python — it argued
against every module the code half needs, because an import cannot be declined. It now says which
files it means.

And a third thing was missing rather than wrong: **a rule is a mechanism**, so it owes the same
four answers as everything else, and its third — who may close it — had never been written down.

## The two findings that were about reliability, and the one that was not

Ranked by *where can a wrong thing pass unnoticed*, which is the only ranking that matters here:

1. **Formats with no contract.** Proved twice in one day, both times by reading rather than by
   running: `docs/manual.md` taught an action wrapped onto a second line whose parser read only the
   first, so a release action printed on a project that has no release; a `source:` line written
   without its hash matched nothing, so an entry that named its source read exactly like one that
   named none, for ever. The fix is a registry that holds each documented example against its
   parser, and a build step that refuses a fourteenth format without one.
2. **The kind of a run, inferred.** Here the review corrected the work: the sixteen ambiguous files
   on live projects were claimed to be features excusing themselves from proof, and **all sixteen
   are genuine errands** — frame children, audit lenses, compose sessions — which the old inference
   had right. The field is insurance with no observations behind the case it prevents. That is worth
   having and is not worth what the first changelog claimed for it.
3. **The Run aggregate having no home** was the headline of two readings, including this session's,
   and it is mostly tidiness: the five copies of the constant never disagreed in the kit's whole
   history. What did disagree were the *questions asked around it* — four programs deciding
   separately what "in flight" means — and one of those was a defect worth the day: the merge guard
   skipped a run file it could not parse, so a project whose files were all broken lost the one
   hook an agent cannot argue with, silently.

## What the day's own review found in the day's own work

Seven defects, three of them introduced by the changes meant to make this harder to fool. Two are
worth remembering as a pattern rather than as incidents.

**A fix can inherit the failure it removes.** The guard was put on a shared module and the import
sat at the top of the file: a half-installed plugin then gave a traceback and nothing else — no
denial, and no sentence either — against a docstring promising it fails open *and says so*. Worse,
the build step written to cover exactly this asked only that nothing be denied, so it passed while
the guard disappeared. A check that cannot distinguish *protected* from *absent* is the same defect
one level up.

**A new rule fires where nobody can act on it.** The kind-unknown finding was reported at every
step, so sixteen finished errands closed with a defect nobody could now fix, straight into a pull
request — the failure the rule three lines below it had already been narrowed to `queued` to avoid.
The lesson is not "narrow it": it is that *when* a finding is asked is part of the finding, which is
the same argument the queue's next item makes about judging a run before it closes.

## What was refused, and why it is not cowardice

- **Splitting `check.py` into modules.** The seams are on the CLI already; splitting produces a
  shared core and mutual references and buys no guarantee. Aggregates and gateways were extracted
  instead — the pieces that carry a rule.
- **A shared `rules/lenses.md`.** The duplicated rules are dispatch rules, read at step zero by one
  of two commands. Moving them costs a hop on the hottest step to save twelve lines. Three of them
  were mechanical and went into `validate.sh` instead, which is the move the four homes actually
  prescribe.
- **A transcript module with fixtures.** A frozen fixture proves this kit still reads yesterday's
  format and says nothing about the day it changes, which is the only day that matters. The useful
  half — asking the live file whether it still carries the fields we came for — is fifteen lines and
  needs no move. Deferred with that written down, so the packaging is not proposed again as though
  it were the guard.

## What is still open

In `docs/planned.md`, items 9 and 10: five small things this review left, and one accepted risk —
`--manual` executing a proof written by a run. The owner was asked and decided to leave it, which is
a decision and not an oversight, and is recorded as one.
