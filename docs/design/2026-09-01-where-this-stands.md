# Where this stands, 1 September 2026

Written for whoever opens a clean session next. Everything here is measured or decided, not
remembered: the four days behind it are in the notes named at the end, and this file exists so the
next session starts from facts rather than from reading them all.

## The numbers, as of S9c

| | |
|---|---|
| `make test` | **1418**, about three and a half minutes |
| `make bench` | **144 of 144** |
| `make armed` | **139 disarm, 5 say in words why nothing can be taken away** |
| branch | `v3`, tree clean |

`make round` runs all three. `make test` deselects two whole-bench measurements and **prints which
target measures them** — that is deliberate, and the note of 31 August explains it.

## What was built in these four days

The seven steps of the layer the plan of 22 August missed, in order, each with a note of its own:
the sitting that writes the knowledge (S8a), the evening composed with the owner (S8b), the audit's
first lens (S8c), the door (S8d), what proves a feature (S8e), the ledger (S8f), manual actions
(S8g). Then the way in for a machine with nothing installed (S9a), two provider declarations (S9),
and the suite made to measure each thing once.

## What is decided, and not open

- **Providers get full access on a development machine.** Claude Code says
  `--permission-mode bypassPermissions`, Gemini `--approval-mode yolo`, Codex
  `--dangerously-bypass-approvals-and-sandbox`. Codex first said `-s workspace-write`, which is a
  *sandbox* rather than an approval mode, and a sandbox has a dependency of its own — bubblewrap,
  absent on this server, so every write failed while the tool reported the workspace as writable.
  Isolation, when it is wanted, belongs around the session (a container, a user of its own), not in
  each tool's own flag: three tools, three mechanisms, three ways to fail quietly.
- **The kit prints commands and runs none.** Not installs, not logins. An installer that reports
  *done* is an assertion; a printed command followed by a re-measurement is a trace.
- **Everything a person reads at the terminal is in Russian.** Code, commits, field names, refusal
  codes and the prose of `method/` — which a session reads, not a person — stay English.
- **No language setting.** A field nobody would set, and guessing at future users is early.
- **A level is measured, never declared.** `provider.toml` says what a provider claims; `agent-kit
  provider check <name>` is what it earns, and it writes what it measured.

## The lesson these four days actually produced

**A declaration written from documentation is a claim, and claims were wrong three times out of
three.** Every one was found by running, never by reading:

| what was wrong | how it was caught |
|---|---|
| `-a never` — the approval flag belongs to `codex`, not to `codex exec` | the ladder |
| `--skip-git-repo-check` missing — a headless session cannot be granted directory trust | the ladder |
| a sandbox instead of full access — writes failed while the tool said they would not | the `writes` rung |
| "a browser will open" — on a server that has no screen, in all three declarations | the owner, running it |

The `writes` rung is the one worth remembering: S9 added it because the probe had always asked
whether a session could create a file and **nobody read the answer**. The first live run it saw
caught a provider that would otherwise have earned level A and silently built nothing, every night.

## What is true of this machine right now

- **Claude Code** — level B, measured 22 August. Working.
- **Codex** — installed, logged in, **level A measured 1 September**. `observed` and `limits` are
  `no`: it does not report context, and it declares no phrase for an exhausted account.
- **Gemini CLI** — installed (`0.57.0`), answers `--version`, **not logged in, level not measured**.
  The owner would rather not buy a subscription; Gemini CLI has historically had a free tier through
  a personal Google account, which is the thing to try before paying.
- **OpenCode** — not shipped at all. Its `run` takes the prompt as an argument while level A pipes it
  on stdin, and the request for `--stdin` is closed as not planned. Its road is `opencode serve`, an
  HTTP endpoint, which is a module rather than a declaration.
- The kit is **not installed globally**. It runs from source, and the owner has an alias:
  `alias agent-kit='PYTHONPATH=/projects/agent-kit/src python3 -m agent_kit'`. That is deliberate on
  a machine where the source changes hourly — nothing to reinstall after a commit.

## The queue, in the order that makes sense

1. ~~**Requirements before installing.**~~ Built, 1 September 2026 —
   `2026-09-01-s9c-requirements-before-installing.md`. `[[provider.requires]]` is a word asked of
   PATH and a line saying why; the walk prints the list marked above the install command, `doctor`
   names what is missing, and so does the ladder's cure. `codex` and `gemini_cli` require `node`,
   measured. What is still open under this heading: a version bound cannot be declared, because
   presence is all PATH answers.
2. **A `writes` failure that names the cause.** It currently says *look at the flag in this
   provider's declaration* — a file the person has not opened and should not have to.
3. **OpenCode**, so that four providers is true rather than a plan.
4. **Gemini measured**, free tier if it exists.
5. **The boundary around a session** — a container or a user of its own, uniform across all four,
   with a rung that measures it. Architectural, not cosmetic, and it needs its own measurement: a
   boundary declared and not measured is what this week already caught twice.

## Blocked, and by what

- **S10** — roles across providers, with fallbacks. Needs measured levels, which needs logins.
- **S11** — AoE as an optional launcher. Its *done when* is *the kit works identically with it and
  without it*, which cannot be checked before one live run without it.
- **S12, S13** — judging a screen. Needs Playwright and a rendering engine.

## Two things the method does not check about itself

Both named in the notes rather than fixed, and both still true:

- **There is no trace of a break round in the repository.** `make armed` answers *does this case read
  its own trap*, not *does breaking this mechanism redden exactly one case*. Every break table in
  these notes rests on a builder's report and a reading of the judges — the S9c table quotes the
  bench's own sentences for its three breaks, which is closer, and still nothing the repository can
  re-run for itself.
- **Nothing has been driven by a live model.** The bench answers from `providers/fake/`. Every note
  says so in its own words, and it is why the first live run of the ladder found four things in an
  afternoon.

## The kit's own ledger

`docs/knowledge/debt.md` — four lines, written by the mechanism S8f built, turned on the repository
that built it: the personal `AGENTS.md` and `GEMINI.md` both tools read against the rule that
reading is not an instruction; the unmeasured levels; the context ceiling with no reader; and
OpenCode's absence. One of them — Codex's level — was closed today by measuring it.
