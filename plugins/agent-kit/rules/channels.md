# Every channel this kit has

Read before adding a record, a file or a field anywhere. **Every mechanism arrives with four
answers** — who writes it, who reads it, who may close it, and what becomes impossible without it —
and this is that table for the channels that already exist. A new one that cannot fill a row here is
not a mechanism yet.

Two things about the table itself. **What is in it is what a program checks**, so it cannot quietly
drift away from what is true: a row whose rule cannot be checked mechanically is written as prose in
the command that owns it, not here. And the storage column is not decoration — the kit has four
kinds of durability, and half the surprises come from a run assuming the wrong one.

| Channel | Written by | Read by | Closed by | Lives |
|---|---|---|---|---|
| `.agent-kit/runs/<slug>/run.json` | every session, about its own run | the session that resumes it, the closing session, the reviewer, the driver, `check.py --run` | the run itself, by a terminal `step` | the machine only — `.agent-kit/runs/` is git-ignored |
| `run.json` → `children` | the composing session; `--advance` while the batch runs | the driver, before every child | the driver, by reaching the end of it | as above |
| `run.json` → `handoff` | the session being handed over | the session that takes it | that same session, by **emptying** it once it has moved everything durable into its own field | as above |
| `run.json` → `manual` | the run that found it — only what needs the owner's hands *and* access | the closing session, composing **Manual actions**; `accept` | the owner, doing it | as above |
| `run.json` → `needs` | the composing session where it knows; the driver, from the frame child's map | the driver, deciding whether a failed feature takes this one with it | the run finishing | as above |
| `run.json` → `frame` | the batch's frame child | the driver, once, the moment that child is built | nothing — the driver applies it and it stays as the record of what was applied | as above |
| `run.json` → `mutation` | the run, from what `commands.mutate` returned | the closing session, into **Proven**; `check.py --run` | the run finishing | as above |
| `run.json` → `proved_at` | the run that last ran the suite — `ship` and `fix` | `check.py --run`, which holds a recorded `suite` to naming a tree in this repository and on this branch; the closing session, which says in **Proven** what the result is bound to | the run finishing | as above |
| `run.json` → `prompt` | the composing session — a command and the child's own directory, never prose | the driver, when it starts the child; `check.py --run` while the child is still `queued` | the run finishing | as above |
| `run.json` → `spent` | the driver, and nothing else | a later gate, pricing a scope | never — it is history | as above |
| `run.json` → `waiting_on` | the session that stopped on a fork, with the owner present | the driver, the window, `next` | the answer landing in `answers` | as above |
| `.agent-kit/runs/<slug>/run.log` | the driver, and nothing else | a person | never — it is history | as above |
| `.agent-kit/runs/<slug>/control` | the owner's window, and nobody else | the driver, between children | the driver, which deletes it as it reads, recognised or not | as above |
| `[driver] …` typed into the window | the driver | the window session | nothing — it is speech | nowhere |
| `[assumed …]` under an entry | `ship` | every later run that builds in that entry | `blueprint`; **or a build command with the owner present**, writing down the answer they just gave | git |
| `[found …]` under `stack.md` | `ship` | `blueprint` | `blueprint`, folding it into the map | git |
| `[frame …]` under `stack.md` | a batch's frame child | every `ship` of that batch, and every later one that opens the map; `agent-kit:reviewer`, judging a diff against it | `blueprint`, folding it into the decisions per area once the batch has merged | git |
| `[stale …]` under an entry | `ship` | every later run that reads that entry | `blueprint`; the closing session, transcribing it; **or a build command with the owner present** | git |
| `[accepted …]` | `advise` | `next`, which raises it | `blueprint`, writing up the record | git |
| an entry's `state:` line | `ship`, the closing session; `next` and `accept` through `check.py --sync`; and `blueprint`, putting one back to `planned` when the owner says the build was wrong | `check.py`, every command | `check.py --sync`, once the pull request merges | git |
| `agent-kit:unmet <key>` beside a test | `ship` | `check.py`, `sprint` with no theme | the `ship` run that makes the promise true, deleting the mark in the same commit — on the decision the owner gave `sprint` | git |
| a part's `walked: <date>` / `derived` in `product.md` | `blueprint`, and only with the owner there | `check.py`, which counts them; `blueprint`; an `epic`'s gate | `blueprint`, when the owner walks that part | git |
| `agent-kit:scenario <heading>` beside a test | `ship` | `check.py --state`, an `epic`'s finish | never — it is the proof itself | git |
| `docs/technical_debt.md` | `ship`, the closing session, and `blueprint` for what the owner brought back from using the product | `check.py`, `sprint`, `next` | the commit that does the work, deleting its line | git |
| `docs/audits/<lens>.md` | that lens | `sprint`, `epic`, `next`, `accept` | the closing session, `next` or `accept`, ticking a box **with its pull request number**; the lens itself, rewriting the file on its next run | git |
| `docs/runs/<slug>.json` | the closing session, from `templates/batch.json` | a later gate, pricing a scope from `spent`; a batch's frame child, reading `per_feature`; `next`, reading `branches` to know which ones a merged pull request delivered; a person | never — it is the durable record of a batch, and `next` deletes the branches without editing the field that named them | git |
| `docs/deployment.md` | any run that finds something only a release needs, while `project.yml` says `stage: development` — the pull request then names the count and not the items | the owner, on the day they first release; the run that finds the next one, so the list stays one list | the owner, doing it — nothing else may delete a line, because nothing else can tell a step that was taken from one that was dropped | git |
| `docs/advice/<lens>.md` | that lens of `advise` | the next run of the same lens, which may not raise a declined row again | that same lens, rewriting the file; git holds the history | git |
| `docs/knowledge/<slot>.md` | `blueprint` and `advise`, with the owner present; a build command, the `state:` line and a block only | every command; `check.py` | nobody — an entry is rewritten, never removed | git |
| `.agent-kit/project.yml` | `blueprint` | every command; `check.py`, which reads the commands and the verdicts | `blueprint`, with the owner — no build command may edit it | git |
| the pull request body and its comments | the closing session | the owner | the merge | GitHub |

## What the check enforces

`check.py` runs before every command, and these it settles rather than trusting:

- **a file in a run directory that is not `run.json`, `run.log` or `control`.** A live run needed to
  start a command the driver could not, so it wrote itself a shell script there and had a session
  execute it — a mechanism with no row in this table, in the one directory nothing tracks;
- **a ticked audit item with no pull request number.** A tick takes an item off every list there is
  — `sprint` reads the unticked half and nothing else — so the number is the only way anyone can
  later check the work behind it was really done. It holds until that lens runs again and rewrites
  the file; a refusal carries the mark `` `declined` `` instead and is not counted;
- **a lens's counters that do not add up.** Every lens warns in prose against narrowing its own
  scope quietly, and three call it countable; the file says what it walked and the check adds it up;
- **a field in a run file the template does not have**, and a `step` no reader knows;
- **a field of records filled with sentences** — answered to a person, empty to every program;
- **a knowledge file the kit ships no template for.** Its fields, its shape and its verdict are all
  keyed off that template, so without one three checks pass it in silence;
- **a finished `ship` or `fix` that left `mutation` empty** where the project declares
  `commands.mutate` — and an excuse there counts only with the command that was run beside it,
  because *the tool would not start* costs nothing to type;
- **a recorded test result bound to no tree**, or to one this repository does not hold, or to one
  the branch being delivered does not contain. Every other field in a run file is that run's own
  account of itself; this is the only claim in it anybody else can check;
- **a child's `prompt` that briefs instead of invoking** — one that does not begin with a command,
  one past four hundred characters, one naming a path inside an installed plugin with a version in
  it. Judged while that child is still `queued`, which is the only moment it can be fixed;
- **a pull request body that puts more in front of the reader than the budget allows**, counted
  before it is opened and counting only what `<details>` does not fold away;
- **a batch that closed without `docs/runs/<slug>.json`**, and **a run that owed a pull request and
  closed with no number**;
- **a batch record whose shape nothing can read** — `spent` written as prose instead of hours,
  features and sessions, `branches` that is not a list of branch names, a count written as a
  sentence. Those two fields are read by a program: a gate prices the next scope from the first and
  `next` clears delivered branches from the second;
- **a file in `docs/audits/` that is neither a lens nor the baseline.** It used to be skipped in
  silence, which made a lens nobody wired in read exactly like a file that is not one.

## Why there is no single bus

Because the readers are not the same reader. `agent-kit:unmet` works precisely because it is a
comment in a source file, found by one `grep` in any language, by a session that is already thinking
about that file. `docs/technical_debt.md` works because a person reads it. `run.json` works because
a program does. Putting them in one transport would make the cheap ones expensive and buy nothing:
what was actually missing was never a bus, it was this table.
