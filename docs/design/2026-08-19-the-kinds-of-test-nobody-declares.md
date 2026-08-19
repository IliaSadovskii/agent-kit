# The kinds of test nobody declares

Written 2026-08-19, from a conversation with the owner, and rewritten the same day after two
reviews cut the proposal to a quarter of its size. **What is described under *What was built* is in
the tree; everything above it is the argument, and everything below *What was rejected* stayed out.**
The same idea was proposed once before and cut in a day, and the reason it was cut turned out to be
the reason this draft was wrong too.

## What the kit already does about tests

Six mechanisms, and they were all checked before anything was proposed:

- **`project.yml` → `commands`** holds `test`, `lint`, `types`, `run`, `e2e`, `mutate`. The manifest
  is the only place a project's real commands are written, and `/agent-kit:blueprint` is the only
  command that may write it (`rules/channels.md`);
- **`check.py --tests`** puts the whole of a project's testing on one screen — what is declared, who
  runs each line and when, when it last ran of record, and whether anything but a session of this
  kit ever runs it. Every column is derived from something that already exists, which is why there
  is no record to keep current;
- **the epic's gate** refuses to start without `commands.run` and `commands.test`, and refuses a
  declared command that starts nothing (`check.py`, `check_epic`);
- **`mutate`** is the only evidence in the kit that a test is able to fail at all, and a feature that
  leaves `mutation` empty on a project that declares the command is a finding;
- **scenarios** are counted against the tests that claim them, by the marker `agent-kit:scenario`;
- **the `tests` lens of `/agent-kit:audit`** walks every entry, line by line, and credits coverage
  only with a file and a line number.

## What none of them answers

The lens measures **whether each line of the description is proven**. Nothing measures **whether the
project owns the instruments that would let a run see its own work at all**.

Those are different quantities, and the second one is what an autonomous run lives on. A front end
with no visual check is a blind spot no number of unit tests closes: the run ships, the suite is
green, and the first person to see the screen is the owner, three batches later.

The lens even carries the legal exit — this is the shape its own documentation gives for one
(`skills/audit/SKILL.md:202`), not a line found on a live project:

```markdown
- [x] `declined`: `moderator.open_queue` — visual only
```

Declined items stay declined and are never raised again — which is right for the lens, whose job is
coverage of a description, and which is exactly how a whole class of surface stays unproven for ever
without any record saying so.

**Empty is a real answer everywhere else too.** `e2e` and `mutate` may be left blank in the manifest,
and the file says so deliberately: the gate names the gap where the owner is standing and the price
of a run is being said aloud. That is a good design for a command that may genuinely not exist. It is
a bad design for the *question* — because nothing anywhere records that the question was asked.

## What one live project measured

Run by hand on 2026-08-19 against `beeplish`, a project that has been on this kit for months and
whose manifest is filled in with care — the point of the exercise was to find out whether the
judging is worth building at all, or whether it would only restate what `--tests` already prints.

What it has: PHPUnit unit and Feature suites, 51 Jest files on the mobile app, ten Playwright specs
run through an Expo web build, `mutate` deliberately empty with the reason written out.

What the walk found, none of it visible anywhere in this kit today:

- **No visual regression at all.** Seven screens, a mobile product, and no `toHaveScreenshot`, no
  Percy, no Chromatic anywhere in the repository. Playwright is already installed and does this out
  of the box, so the gap is nearly free to close and nothing points at it.
- **No contract test against seventeen declared integrations.** Wikiquote, Wikidata, Gutendex, VOA,
  Stack Exchange, OpenRouter, Google and Apple sign-in. Each can change its answer silently while
  every test stays green, because every test goes through a stand-in. The `tests` lens flags this one
  feature at a time, in the citation, and no one place adds them up.
- **No static analysis of the backend.** `require-dev` carries Pint, which formats and does not
  analyse; there is no PHPStan, no Larastan, no Psalm. `commands.types` is declared as
  `cd apps/mobile && npm run typecheck`, so it covers the mobile half only — while the manifest's own
  comment says the backend carries almost all of the product's logic.

The third one is the reason the field is not called *kinds of test*. `--tests` prints `types` as
declared and says nothing, because a string is there and it runs. That it checks half the project is
invisible from every record the kit has. **A `yes` therefore has to mean *covers this project*, not
*exists somewhere in it*.**

## Why the earlier version of this was cut

A `tests:` table in the manifest was proposed on 17 August 2026 and cut the same day
(`docs/planned.md:477`). The words were: *four fields of prose in a config file with no reader and no
closer*, and the column it wanted to fill — when each kind last ran — was to come from `gh run list`,
which answers per workflow run and knows nothing about a kind of test.

That verdict stands, and any new proposal has to differ from it in the two places it named. The
difference here is that the field records **a decision**, not an inventory: what this project will and
will not be able to see, taken once by the owner, closable by them, and read at the gate. An
inventory of what exists can be derived — and already is, by `--tests`. A decision cannot be derived
from anything.

## What was built, after two reviews cut it down

The first draft of this note proposed a read-only subagent invoked from every build command's gate,
a fixed list of seven kinds in the manifest, and a four-way table of what to do with the work
depending on what was launched. Two reviews — one against the kit's own laws, one run by hand
against `metsomeone` and `realest` — returned **DO NOT BUILD** and **BUILD WITH CHANGES**, and both
broke it in the same place. What shipped is a quarter of it.

**The break: the gate that asks may not write the answer.** The verdict of 17 August named *three*
reasons, and this note answered two of them and dropped the third — *into a file only `blueprint`
may write*. A question put in `rules/preflight.md` is a question asked by `ship`, `sprint` and
`epic`, and `rules/channels.md` says no build command may edit `project.yml`. So the owner answers,
the answer has nowhere to go, and the next run asks again — for ever. `asking.md` forbids exactly
that: *never ask a question nobody can act on*. The mechanism would have become the alarm it opened
by describing.

**So `blueprint` judges and writes, in step 3.** Which turned out to need no new machinery at all:
that step already runs one bounded research pass with delegation, already settles `tests.unmet` and
`commands.mutate` in the same breath, already returns *a proposal, never a written record*, and is
the one command allowed to write the file. The subagent argument was half a quotation — the audit
gives each lens its own subagent for a *full* run, and the same file continues: *a single-lens run
does the work inline, where a subagent pays the cost of orienting itself for context the session
already has*. This is that case.

**And the field shrank to what cannot be derived.** `print_tests` says it in its own docstring:
*everything about this project's testing on one screen — derived, never declared. A declared table
would have been four fields of prose in a config file with no reader, which is what the first draft
of this was.* Of the seven proposed kinds, `e2e`, `mutation`, `static_analysis` and the unit /
integration split are all read off `commands` and printed already. Two are not: `visual` and
`contract`. Those two shipped, and nothing else.

## The mechanism, as it stands

```yaml
commands:
  visual:            # what compares a screen against how it looked before
  contract:          # what holds a real outside service, or a published API, to its shape
tests:
  visual:            # no <date> <reason> — only where the command above is empty
  contract:          # no <date> <reason>
checks:
  sight_reviewed:    # the date the pair was last taken with the owner
```

**The claim is a command and never a word**, and this was the last thing to change. The first
version of the field took `yes`, and the owner asked the question that killed it: what checks that a
`yes` is true? Nothing did. A project could carry `visual: yes` with no visual test in it and every
check in this kit would agree — while `commands.test: make test` on a project with no makefile is
caught, because that rule was learned by a child meeting an unrunnable suite at three in the
morning. A word that nothing can start is that same defect with the lesson removed.

Putting the claim in `commands` fixes the other half at the same time. A command is not only
checkable, it is **runnable** — so `ship` can run `visual` on a feature that changed a screen, and a
batch's closing session can run `contract`. Storing a verdict would have left the kit knowing a
project owns an instrument and never starting it, which is the shape of the finding this whole note
began from: an instrument installed, configured and never declared.

- **`blueprint`, step 3** judges both — **from the repository, never from `stack.md`**, which is the
  finding the second review paid for: on `metsomeone` the stack slot said mutation testing was not
  installed while `pest-plugin-mutate` was a hard dependency of Pest 4 and `phpunit.xml` had already
  been tuned for it, and `scripts/visual-audit.mjs` walked all twelve screens in two viewports
  asserting nothing, mentioned in no document at all. Dependency manifests, test directories, CI
  workflows and scripts. The cheapest finding on both live projects was an instrument installed,
  configured and undeclared.
- **`check_sight`** holds a declared command to starting — the same `command_defect` every other
  command here is held to — and a refusal to a date and a reason. It judges no prose beyond finding
  a date in it. Both at once is its own finding: a project cannot refuse a thing and run it.
- **`ship` gained a step**, and `WHO_RUNS` gained two rows, so `--tests` answers *who runs this and
  when* for these the way it does for everything else.
- **Printed under `--status` and `--state` only** — the seam `outside_line` already uses, and for
  the reason written there: said six times a night in sessions nobody is watching it is noise; said
  once where a person typed the command it is a question they close in a minute. `ship` runs the
  check bare and never sees it, which is correct — that session could not write the answer anyway.
- **Never an exit code.** Every project adopted before this existed has two unanswered verdicts and
  none of them is broken.
- **One row in `preflight.md`, and it forbids asking**: name it, offer `blueprint`. The same shape
  the table already uses for a declared command that starts nothing.
- **The shape check stands aside on these three keys**, or the same fact arrives twice in two
  voices — *behind, and not yours to move* from one, *close this today* from the other.

## The four answers, for the shape that shipped

| | |
|---|---|
| **Who writes it** | `verification.yml` is the kit's, changed by a commit to the kit; a project's answers are `blueprint`'s, with the owner, in step 3 |
| **Who reads it** | `check.py` — `check_verification` for the answers, `check_epic` at the gate, `run_defects` for what a feature ran, `--tests` and `--owed` for the screens; `blueprint`, walking the list; `ship` and `fix`, choosing what this change owes; an epic's proving phase; `agents/reviewer.md`, holding a `why` against the diff |
| **Who may close it, and where** | **a kind**: the owner, through `blueprint`, with `no <date> <reason>` — and the date reopens it at six months or when a dependency manifest moves. **A kind of the kit's**: a commit deleting its entry in `verification.yml` and the test naming it. **The mechanism itself**: a commit deleting `verification.yml`, `catalogue`/`answers`/`refusal`/`unanswered`/`check_verification`/`check_reviewed`/`print_answers`/`print_owed`/`print_outside`, the `verified` block in `run_defects`, the gate clause in `check_epic`, `VerificationCase` and `VerifiedFieldCase`, the `verification` and `checks.verification_reviewed` keys in the template, the `verified` field in `templates/run.json`, and the steps in `blueprint`, `ship`, `fix` and `epic/references/finish.md` — in one commit |
| **What becomes impossible** | a project quietly owning no way to see a class of its own surface, and a feature quietly not running what its project does own |

## What was rejected, and by whom

- **A subagent at every build command's gate** — the gate cannot write the answer, and `blueprint`
  already has the context. Both reviews.
- **A fixed list of seven kinds** — four of them are already derived from `commands`, and a fixed
  list inside a nested key is invisible to the shape check, which compares only one level deep. So
  an eighth kind added to the template would have appeared in no project and nothing would have
  said so. First review.
- **A four-way table of where the work goes** (`epic` → first batch, `sprint` → batch, `ship` →
  debt, `next` → a rung). `preflight.md` states the rule for exactly this case: *promises the
  product does not keep are read differently by each command, so that row lives in the command
  rather than here*. And the second review priced the `epic` half on a real project: PHPStan on a
  live Laravel with Filament and Livewire produces hundreds of findings on untouched code, so batch
  zero either goes red at night with nobody there or installs a baseline that leaves every later
  feature a step that is already failing; visual baselines over a script carrying
  `waitForTimeout(3000)` on a d3 map and `8000` on an LLM translation flake from day one; contract
  tests against OpenRouter need a live key in CI and cost money per run, on a project whose
  `phpunit.xml` deliberately blanks that key so no test reaches the network. **What survives of that
  argument** — an instrument installed after thirty features arrives after the work it was for — is
  true, and the answer is at most one, the cheapest, chosen by the owner. Written down here rather
  than built.
- **A line telling the installing run to write `[found …]`** — `ship/SKILL.md` already carries that
  rule and calls it *the only route by which the library map learns anything*. A second copy inside
  generated prose is the home with no barrier to entry and no check.
- **Asking on every tool call** — only a hook fires on every call, and a hook cannot ask.
- **A tick instead of a date** — a project that grows a front end after the tick reads as settled
  for ever.

## Open

- **`no` is closed by a date and nothing else.** Nothing watches whether the product grew the
  surface the `no` was about — a project that adds a front end waits up to six months to be asked
  again. Watching `screens.md` for it was considered and not built: the check would fire on every
  planned screen, and most projects describe screens long before they have any.
- **`visual` and `contract` are each one word for more than one thing.** `contract` on `beeplish`
  and `metsomeone` means the outside APIs they consume; on `realest` it means the OpenAPI document
  they publish, which nothing verifies. One verdict covers both, and the reason line is where the
  difference has to live.
- **`contract` has no field of its own on a run.** `mutation` does, which is why a feature that
  skipped it and one that passed it cannot read alike. The closing session runs `contract` and
  reports it in prose, and prose is what the kit has been removing from its records for six
  releases.
- **Nothing counts what this is worth.** The claim is that a run which cannot see a screen ships
  worse work, and it is a belief, not a measurement. What could be measured: how many defects
  reaching `accept` are visual on projects with a `no` against those with a `yes`.

## Cost

One field read per check. `blueprint` pays for the judging once per project per six months, inside a
research pass it was already running.

## What 2.28.0 changed, the day after

The two kinds above shipped hard-wired into the manifest — `commands.visual`, `commands.contract` —
and the owner refused that shape on sight: **naming the kinds in the code is a decision about every
project, taken by whoever wrote the check.** The kinds a project needs follow from its stack. What
belongs in the kit is the list of questions.

So the list moved into `verification.yml` inside the plugin — twelve kinds, each with what it
catches and which session runs it — and the manifest holds only this project's answers, one line per
kind. A kind added to that file starts being asked of every project on its next check.

Four things came with it, and they are the owner's four requirements rather than anything this note
worked out:

1. **the answers are taken once, with the owner, against the whole list** — `blueprint`, step 3;
2. **a feature runs what its project answered for and records what came back** — `run.json` →
   `verified`, and a kind left silent is a finding, because silence reads exactly like a pass;
3. **an epic will not start on a kind nobody answered** — the one place in the kit this stops
   anything, and it is where the owner is standing;
4. **the answers go stale on evidence** — six months, or a dependency manifest whose hash has moved,
   because a stack that changed is a stack whose answers were taken about a different project.

What survives from this note unchanged: the diagnosis, the refusal-with-a-date, the rule that a
claim is a command and never a word, and every entry under *What was rejected*.

## What the review of 2.28.0 caught, and it is worth writing down

Thirteen findings, and three of them were the same mistake in different clothes — **a rule that was
enforced somewhere and then moved**:

- **A refusal needed a reason in 2.27.0 and did not after the move.** `refusal()` returned the
  moment it found a date. Every document still said `no <date> <reason>`; the program had stopped
  asking. Twelve lines of `no 2026-08-20` cleared a gate that blocks every project on this kit, and
  recorded nobody having thought about anything — the exact confusion the mechanism exists to make
  impossible. It is restored, and it is now what `unanswered` tests too, so the gate cannot be
  cleared by a shaped answer.
- **`print_outside` re-asked a question `outside_a_session` already answers in four ways**, forty
  lines below it, and got it wrong in both directions — including the fourth answer's own case, a
  command declared as `docker compose exec …` and run in CI under another name.
- **`check_reviewed` re-walked `checks.deps` that `check_stack` walks**, so a moved manifest was
  reported twice in one run.

The largest single fix was **two homes for one fact**: `commands.test`/`lint`/`types`/`e2e`/`mutate`
already existed, and the catalogue asked for the same five again under its own names. A project with
a working suite, linter, type checker and browser runner — all four in CI — was told on one screen
that nobody had been asked about any of them, and refused an epic on that basis. Five kinds now
carry `command:` in the catalogue and are answered in `commands` and nowhere else; the refusal for
them still lives in `verification`, because `commands` has nowhere to put a reason.

And two the mechanism could not have caught about itself: the guard hook would have refused
`playwright test --grep @visual` on a project whose `commands.e2e` is `playwright test`, because the
one string contains the other — on every feature that touches a screen; and `skip_when: never` was a
word in a file no program read, so a feature could excuse itself from a kind that applies to every
project there is.

What the review confirmed as sound: the shape, `run_defects`' scoping, the exit-code seam, and that
this version clears all three reasons the `tests:` table was refused on 17 August.

## The second review, and the pattern in what both of them found

Nine more findings, and the pattern is now unmistakable: **a rule enforced in one place, then moved,
loses its enforcement and its test in the same movement.** Four rules died that way in one day —
the reason on a refusal, the contradiction between a command and a refusal for one kind, the
four-answer form of *does anything outside this kit run it*, and `skip_when: never`. Each was
replaced by a docstring saying it still held. The suite was green over all four, because the tests
went out with the code they guarded.

The most dangerous finding was not in the mechanism at all. The guard hook's exemption for a
feature's own visual command was written as an early `return None` **above** the rules that refuse
merging, force-pushing and pushing to the default branch — so naming a declared command anywhere in
a line stood the whole hook aside. It shipped with no test. That file's own docstring calls it *the
one mechanism an agent cannot talk itself out of*.

Two lessons worth keeping, and they are about method rather than about tests:

1. **When replacing a mechanism, list what the old one enforced before deleting it**, and move the
   tests first. A test deleted with the code it guards leaves a green suite over a hole.
2. **An exemption belongs inside the rule it exempts**, never above a run of them. The shape of the
   defect — one condition placed one line too early — is invisible in a diff and total in effect.
