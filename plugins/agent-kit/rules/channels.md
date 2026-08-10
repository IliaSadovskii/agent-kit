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
| `run.json` → `handoff` | the session being handed over | the session that takes it | that same session, by overwriting it | as above |
| `run.json` → `prompt` | the composing session | the driver, when it starts the child | the run finishing | as above |
| `run.json` → `spent` | the driver, and nothing else | a later gate, pricing a scope | never — it is history | as above |
| `run.json` → `waiting_on` | the session that stopped on a fork | the driver, the window, `next` | the answer landing in `answers`, or the deadline | as above |
| `run.log` | the driver, and nothing else | a person | never — it is history | as above |
| `control` | the owner's window; `--advance` | the driver, between children | the driver, which deletes it as it reads | as above |
| `[driver] …` typed into the window | the driver | the window session | nothing — it is speech | nowhere |
| `[assumed …]` under an entry | `ship` | every later run that builds in that entry | `blueprint`, rewriting the entry | git |
| `[found …]` under `stack.md` | `ship` | `blueprint` | `blueprint`, folding it into the map | git |
| `[stale …]` under an entry | `ship` | every later run that reads that entry | the closing session, transcribing it; or `blueprint` | git |
| `[accepted …]` | `advise` | `next`, which raises it | `blueprint`, writing up the record | git |
| an entry's `state:` line | `ship`, the closing session, `next --sync` | `check.py`, every command | `check.py --sync`, once the pull request merges | git |
| `agent-kit:unmet <key>` beside a test | `ship` | `check.py`, `sprint` with no theme | `sprint`, once the owner says which side is wrong | git |
| `agent-kit:scenario <heading>` beside a test | `ship` | `check.py --state`, an `mvp`'s finish | never — it is the proof itself | git |
| `docs/technical_debt.md` | `ship`, the closing session | `check.py`, `sprint`, `next` | the commit that does the work, deleting its line | git |
| `docs/audits/<lens>.md` | that lens | `sprint`, `mvp`, `next` | the closing session or `next`, ticking a box **with its pull request number** | git |
| `docs/runs/<slug>.json` | the closing session | a later gate; a person | never — it is the durable record of a batch | git |
| the pull request body and its comments | the closing session | the owner | the merge | GitHub |

## What the check enforces

`check.py` runs before every command, and these it settles rather than trusting:

- **a file in a run directory that is not `run.json`, `run.log` or `control`.** A live run needed to
  start a command the driver could not, so it wrote itself a shell script there and had a session
  execute it — a mechanism with no row in this table, in the one directory nothing tracks;
- **a ticked audit item with no pull request number.** Both things allowed to tick one are required
  to name it, and the next `sprint` composes a batch from that list;
- **a field in a run file the template does not have**, and a `step` no reader knows;
- **a field of records filled with sentences** — answered to a person, empty to every program.

## Why there is no single bus

Because the readers are not the same reader. `agent-kit:unmet` works precisely because it is a
comment in a source file, found by one `grep` in any language, by a session that is already thinking
about that file. `docs/technical_debt.md` works because a person reads it. `run.json` works because
a program does. Putting them in one transport would make the cheap ones expensive and buy nothing:
what was actually missing was never a bus, it was this table.
