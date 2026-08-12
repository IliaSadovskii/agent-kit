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
| `run.json` | every session, about its own run | the session that resumes it, the closing session, the reviewer, the driver, `check.py --run` | the run itself, by a terminal `step` | the machine only — `.agent-kit/runs/` is git-ignored |
| `run.json` → `children` | the composing session; `--advance` while the batch runs | the driver, before every child | the driver, by reaching the end of it | as above |
| `run.json` → `handoff` | the session being handed over | the session that takes it | that same session, by **emptying** it once it has moved everything durable into its own field | as above |
| `run.json` → `manual` | the run that found it — only what needs the owner's hands *and* access | the closing session, composing **Manual actions**; `accept` | the owner, doing it | as above |
| `run.json` → `needs` | the composing session where it knows; the driver, from the frame child's map | the driver, deciding whether a failed feature takes this one with it | the run finishing | as above |
| `run.json` → `frame` | the batch's frame child | the driver, once, the moment that child is built | nothing — the driver applies it and it stays as the record of what was applied | as above |
| `run.json` → `mutation` | the run, from what `commands.mutate` returned | the closing session, into **Proven**; `check.py --run` | the run finishing | as above |
| `run.json` → `prompt` | the composing session | the driver, when it starts the child | the run finishing | as above |
| `run.json` → `spent` | the driver, and nothing else | a later gate, pricing a scope | never — it is history | as above |
| `run.json` → `waiting_on` | the session that stopped on a fork, with the owner present | the driver, the window, `next` | the answer landing in `answers` | as above |
| `run.log` | the driver, and nothing else | a person | never — it is history | as above |
| `control` | the owner's window, and nobody else | the driver, between children | the driver, which deletes it as it reads, recognised or not | as above |
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
| `docs/runs/<slug>.json` | the closing session | a later gate; a person | never — it is the durable record of a batch | git |
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
- **a batch that closed without `docs/runs/<slug>.json`**, and **a run that owed a pull request and
  closed with no number**.

## Why there is no single bus

Because the readers are not the same reader. `agent-kit:unmet` works precisely because it is a
comment in a source file, found by one `grep` in any language, by a session that is already thinking
about that file. `docs/technical_debt.md` works because a person reads it. `run.json` works because
a program does. Putting them in one transport would make the cheap ones expensive and buy nothing:
what was actually missing was never a bus, it was this table.
