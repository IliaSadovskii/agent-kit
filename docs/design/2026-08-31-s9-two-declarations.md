# S9 — adapters two to four, of which two

Written after building it, 31 August 2026, the same day as S9a, which built the walk these
declarations feed.

> **S9 · Adapters two to four.** Codex, Gemini CLI, OpenCode. Each is a config block plus a small
> module, and each is run through the bench for its level. The context ceiling is measured per
> provider, never inherited.
> *Done when* the bench reports a level for each, and the numbers behind each ceiling are written down.

## 1 · The cut, and what the owner does not have to do first

Nobody here had installed or logged into any of the three, and asking the owner to do that before
the step would have put the work in the wrong order: without declarations, `agent-kit setup` does
not know what to print, so there is nothing to walk anybody through.

So this step ships **declarations only**, at level A, each carrying the install and login commands
the walk prints. No level-B modules, no claim about any tool's real level. What the owner runs
afterwards closes the rest, and it is named at the end of this note.

**Two declarations, not three.** OpenCode does not fit, and not because it is not installed.

## 2 · OpenCode, and the sentence in the plan that was wrong

Level A in this kit is `ProcessExecutor`: one composed input **on stdin**, one answer on stdout.
`opencode run` takes its prompt as a positional argument and does not document reading stdin; the
tracker's request for `--stdin` — raised for exactly this, large prompts hitting `ARG_MAX` — is
closed as not planned. A declaration with no `headless` flag would produce `["opencode"]`, a TUI
hanging until the session timeout half an hour later.

The alternative was considered and refused with a reason rather than a taste: passing the input as
a positional argument means a new declaration key, a branch in the executor, and a 128 KiB ceiling
per argument against inputs that are already tens of kilobytes. Its road is `opencode serve`, an
HTTP endpoint — which is a Python module, which is level-B work outside this cut.

**What the plan got wrong is subtler than "OpenCode is not the cheapest".** §3 says it reaches
level B without parsing a transcript, and that is still plausible. The unexamined assumption is
that its headless mode would fit the kit's stdin shape at all. That is the sentence to correct.

## 3 · What a declaration nobody here has run may say

Every key is a claim about somebody else's tool. Three of the first draft's claims were wrong, and
the review caught all three against the tools' own documentation:

- **`codex exec` sandboxes to read-only unless told otherwise.** A declaration without a
  full-access flag would have shipped a provider that cannot create a file — and the plan's own
  §3 would have called it level A. It declares `-s workspace-write -a never`: a run builds inside
  its own worktree, so the workspace is the whole of what it has any business editing, and there is
  nobody at the terminal at three in the morning to approve anything.
- **`--yolo` is deprecated in Gemini CLI** in favour of `--approval-mode`.
- **`headless = ["exec", "-"]` would have put a positional argument before every flag**, because
  `command()` appends flags after the headless ones. It is not needed: given no prompt argument,
  `codex exec` reads stdin. So `["exec"]`.

**And "declare no level" turned out to be impossible.** `Declaration.read` defaults `level` to `A`,
silently, and that default flows into `earns_what_it_declares`. Rather than invent a third state,
both declarations say `level = "A"` outright and say in their own prose that this is a claim the
ladder has not measured — which is also what the screen prints: *declares A · never measured
against an account*.

## 4 · What is deliberately blank, and what each blank costs

`[provider.answer]` and `[provider.transcript]`: level A has no reader for either — `execute`
returns raw stdout, and the answer keys are read only by Claude Code's adapter.

`[provider.limits]`, and this one has a price worth naming. The `limits` rung does not measure the
tool: it takes the declared phrase, builds a sentence out of it, and checks that the kit's own
regex finds it — its own writing, graded by itself. Declaring phrases nobody has seen these tools
say would earn a green rung for nothing, and a wrong phrase is worse than none: a failed session
whose stderr happens to contain *rate limit* would become unretryable with an invented reset hour.
**The cost of leaving it out is real and is written into the declaration**: an exhausted account
comes back as an ordinary retryable failure, so the attempt chain spends all three tries with the
pause doubling between them.

`flags.effort`: Codex sets reasoning effort through a config override, not a flag carrying a value,
and the declaration's shape cannot express it. Gemini has no such idea at all.

`flags.instructions`: neither tool has an equivalent of `--setting-sources project`, so both read
the operator's personal `AGENTS.md` / `GEMINI.md`. **That is against the kit's own rule that
reading is not an instruction**, and it cannot be fixed by a declaration. It is a line in the
ledger, not a footnote.

## 5 · Four holes the step exposed in the kit, and two it refused to fix

Declaring a second and third provider made four latent defects reachable, and each is fixed here
because S9 is what makes them reachable:

- **`flags.*` and `answer.*` were never validated.** A typo was silently ignored — and the Gemini
  declaration deliberately has *no* headless key, so `hedless` would have produced identical argv
  and been indistinguishable from correct.
- **A model the machine names was dropped in silence** when the provider declares no model flag.
  It is a refusal by name now, before anything is spent.
- **`can_write` had no reader.** The probe has always asked whether the session could create a file
  and delete it again; nothing read the answer, so a provider that cannot write earned level A. The
  ladder has a `writes` rung now — and Codex, sandboxed to read-only by default, is exactly the
  provider that makes it matter.
- **A bare `agent-kit setup` walked to the alphabetically first not-ready provider**, which on a
  working machine means walking somebody towards installing Codex when Claude Code is fine.

Refused, with reasons: **the promised refusal of a level-A provider in an unattended role is
S10** — the config has no notion of *unattended*, and inventing one in passing is how a field with
no reader gets born. **A reader for the context ceiling is a step of its own** — level A cannot
observe it at all, so nothing here brings it closer.

## 6 · The numbers, measured by hand

| | before | after |
|---|---|---|
| `make test` | 1339 | **1368** |
| `make bench` | 139 of 139 | **142 of 142** |
| `make armed` | 134 + 5 in words | **137 + 5 in words** |

Three traps; the bench also ran 142 of 142 from `git archive HEAD` unpacked elsewhere, and
`make install-check` confirms the wheel carries both new declarations.

**My own verification run had one failure, and it is not the step's.**
`test_every_shipped_case_fires` reported `plant.sh exited with 137: Killed` for one world — a
SIGKILL from the out-of-memory killer on a server with 11 GB shared between projects. The
standalone `make bench` in the same batch passed 142 of 142.

This is the third sighting of the tail the owner named at the start, and it now has two measured
causes rather than one: a 300-second timeout (S8e) and an OOM kill (here). Both have the same
root, which was measured on the first night of this build and never fixed: **the suite runs the
whole bench twice and the disarm once inside itself**, so a routine `make test` measures 142 worlds
three times over while `make bench` and `make armed` exist as separate targets anyway. Eleven and a
half of the suite's twenty-five minutes are those three tests.

## 7 · Breaking it by hand

| broken | what said so |
|---|---|
| a bare walk goes back to "whoever needs the walk first" | `a-walk-that-stays-where-it-works` |
| the `writes` rung stops reading `can_write` | `a-session-that-cannot-write` |
| the walk runs the declared login itself | `a-provider-nobody-here-has-run` |

Two breaks were wrong and are recorded rather than tidied away. One reddened *three* cases — the
break took the shim's stdin with it, so it was too wide, not the judges. The other reddened
nothing: the case's own expectation **is** a refusal, so a provider left permanently not-ready
keeps every claim true — the same mistake S9a's note already describes, made again.

## 8 · What the traps can and cannot prove

The bench installs nothing and reaches no network, and the catalogue is the package's own folder —
a case cannot plant a provider of its own. So the shims are written **from the tools'
documentation**, not from the kit's declaration, and the case measures whether the kit's
declaration matches what the builder read. That is a real thing to measure — change `headless` and
the case reddens — but it says nothing about the tools themselves, and that sentence is printed in
the judge's own refusal text rather than left in a comment, because a comment is not printed when a
case goes red.

Held by tests and said in words: the validation of `flags.*` / `answer.*` keys, and the refusals
for a model or an effort the tool cannot be told. To disarm either, a case would have to take an
*absent* key away from a shipped declaration, and the shipped declaration is the kit itself.

## 9 · What was not confirmed, named one by one

Not "mostly verified" — these are the specific claims nobody has stood behind with a machine:

1. `codex --version` — not in the published reference of global flags. *(Since measured on the
   owner's server, where Codex was installed forty days before this step: it answers
   `codex-cli 0.144.6`.)*
2. What `codex exec` does when an approval is missing — waits, refuses, or silently skips the edit.
3. The syntax of the config override for reasoning effort.
4. **The context ceiling of either tool.** Neither is confirmed by documentation, which is the
   second half of the *done when* and the reason it is reformulated rather than claimed.
5. That `gemini` goes non-interactive on a pipe, and that `codex exec` with no argument reads
   stdin. Both from documentation, neither from a machine.

## 10 · The *done when*, reformulated honestly

The plan asks that the bench report a level for each and the ceiling numbers be written down. The
bench does report a level — against a shim. What it cannot report is *whose* level that is. And
`observed` is always "no" at level A, because only a level-B adapter fills in the session's facts,
so no ceiling number can come from any amount of work inside this cut.

So: **two declarations shipped; the bench measures the shape of level A against a shim written from
the tools' documentation; OpenCode deferred with its reason recorded; and what is not measured is
named one by one** — the account, each tool's real level, the context ceiling — with one command
that closes it:

```
agent-kit setup codex && agent-kit setup gemini_cli
agent-kit provider check codex && agent-kit provider check gemini_cli
```

Each `check` writes what it measured, so a level stops being a claim without anybody's word for it.

## 11 · The kit opened a ledger on itself

Four lines in `docs/knowledge/debt.md`, written in the format `record` writes and verified by
reading the file back rather than by looking right: the personal instruction files both tools read;
the unmeasured level of both; the context ceiling with no reader; and OpenCode, absent with its
reason. This is S8f's mechanism turned on the repository that built it.
