# What the first review changed, 22 August 2026

S0, S1 and S2 were read back against the plan by a reviewer that had the plan and the code and
nothing else. Two findings were blocking. Both were the same shape, and it is the shape the
measurement was written about: **the program said one thing and the record said another.**

## The two that mattered

**A run that "stops" did not stop.** `finished` covered `done` and `stopped` only, so after three
refusals and the fallback the next `step run` resumed the run as if nothing had happened — and
`start_step` cleared `run.reason` on the way, deleting the recorded failure. The attempt
directories still held the evidence; the record a daemon or a person would read did not.

Now `failed` is one of the three ways a run is finished, and the step status machine has a new
verb: an attempt that was refused **refuses the step** (it returns to pending, keeping its reason,
the run stays running) while an exhausted policy **fails** it (the step and the run both stop).
Two different events had been sharing one word.

**The `kit` field had no reader.** Every `run.json` said which kit wrote it and nothing ever
looked. Open question 3 asked for the opposite — refused if newer, migrated if older — and rule 5
forbids a field with no consumer, in the one file rule 4 says is most expensive to change later.
A file from a newer kit is now refused by name (`kit-too-new`), same release compared, dev
suffixes ignored.

## The rest, in one line each

| What | What was done |
|---|---|
| the adapter contract lived in `driver/` | moved to `providers/base.py`, the file the plan names as the only one that defines it |
| the CLI named providers in its own code | `providers/registry.py` reads the folder; `--provider` and `--option KEY=VALUE` carry the rest, and `agent-kit provider list` is measured from `provider.toml` |
| the fallback attempt was told "attempt 4 of 3" | attempts are counted per provider for the agent, cumulatively for the record |
| a fallback that repeated the primary got a fourth turn | it is dropped from the chain |
| `method/rules/output.md` restated a constant, wrongly | the prose points at the input's own head instead |
| `.gitignore` hid the second version's run state, not the third's | `.agent-kit/` |
| `findings` / `severity` shipped on `probe` with no reader | removed until the deliver step can refuse on one |
| `account`, `roles.model`, `roles.effort` were parsed and never shown | `config show` prints everything the configuration holds |
| `daemon_db`, the project's `project.toml` path, `skip_step` | deleted; they arrive with S7, S4 and question 9 |
| the version lived in two files | `pyproject.toml` reads it from the module |
| an enclosure containing a fence broke the input | the fence is now longer than any inside the body |
| `RunStore` imported the step registry | creating a run moved to `driver.create_run`, so the arrow keeps pointing one way |
| open question 13 said "the kit's own CI" and there was none | `.github/workflows/tests.yml`: the suite, plus the install path S0 promised |

## The environment, reviewed separately

A second reviewer read only the packaging, the container and the server's project contract. The
contract is met requirement by requirement, and `uv tool install` was verified end to end from a
clean `git archive` — the wheel carries `method/` and `provider.toml`, and `method_root()` was
checked in both of its branches, installed and checkout. One finding was blocking:

**`uv sync` rewrote the committed lock at every container start.** No `--locked`, so `make up`
silently re-resolved and left the working tree dirty from a command whose job is to raise the
workshop — the pinned environment was never the one anybody reviewed. Now the start checks the
lock and refuses to re-resolve; a lock that has drifted says so. A start with no network keeps the
environment the image already has rather than restart-looping, because a workshop that was fine
yesterday is fine today.

The rest: the interpreter is pinned like the rest of the toolchain (`python:3.12.14-slim`, uv was
already pinned); `requires-python` narrowed to `>=3.12`, which is what is actually tested;
`make test` and `make install-check` now depend on `make up`, so neither can run against a
workshop nobody raised; `dist/` ignored; and — the one that would have bitten quietly —
**no test can reach the home of whoever runs it**. `main()` reads the real environment and the
logger writes under `~/.local/state`, so a single test that forgot to redirect `HOME` would have
written there. `tests/conftest.py` now redirects it for every test, autouse, rather than trusting
each one to remember.

## The code, reviewed a third time

A third reviewer read only the code, ran it, and proved every finding by hand. Four were blocking,
and three of them were the same defect wearing different clothes: **a failure the state could not
be moved out of.**

**Any exception that was not `ExecutorFailed` wedged the run.** The driver caught the one failure
it had named and let everything else escape — after the step was already committed to disk as
running. The run was then unadvanceable: `run_next` said *every step is done* about a run where
nothing was, and `run start` said the step was already running. Only a lie (`run pass`) got out.
An adapter is somebody else's code around somebody else's CLI; a surprise from it is now an
attempt that did not work, recorded as `provider-crashed` with the exception's type, and the retry
policy takes it from there. Whatever else escapes, the step is returned to pending with the reason
written down before the exception is raised on. And `main()` no longer spills a traceback: an
unhandled failure is `internal-error`, exit 70, with the whole of it in the log.

**A killed driver left a step running and nothing could pick it up.** Now the next run says so —
*the driver that started this step never came back* — returns the step to pending and tries again.

**`fail_step` rewrote a step that had passed.** With no step running it reached for the last one
touched, unguarded, so a step with its `output.json` on disk could be rewritten as the failure.
It now requires a running step, and the run-level failure skips whatever passed.

**No migration could ever have run.** `OLDEST_SCHEMA` tracked `SCHEMA_VERSION`, so the first real
migration would have been refused as *too old* before the loop that applies it was reached — and
the test hid it by patching that very constant. How old a file may be now follows from the
migrations themselves; registering one is the whole of it.

The rest: a role in the configuration no longer overrules the provider a person typed; `step input`
refuses a run that is over; a malformed `provider.toml` is refused by name instead of raising, and
one with no `[provider]` table no longer passes itself off as a real level-A agent; `release()`
reads a version written the way people write it, with a `v`; an enum that names no choices is a
defect at declaration rather than a field that refuses everything; and a fence whose tag shares a
line with the output is found.

## The one that is not a code change

The reviewer's sharpest note: **"the test is written first" is prose that nothing checks, and the
commit messages asserted compliance with it.** That is precisely question 2 — *a claim the same
model makes about its own work* where a trace was owed.

The claim is gone from the commit messages. In its place there is a trace: from here on the tests
land in their own commit, before the commit that makes them pass. Anybody can read the history and
see whether the rule held; nobody has to believe a sentence about it.

The third review put teeth in that as well, by naming four tests that would have passed with the
code wrong: the migration test that patched away the constant hiding the defect; a test named for a
branch it did not exercise; a retry test that would have passed had the refusal never been
enclosed; and a comparison between two values that can never be equal. All four are replaced. A
test that cannot fail is prose with a green tick, which is worse than prose.
