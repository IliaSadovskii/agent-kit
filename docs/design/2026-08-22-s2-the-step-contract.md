# S2 — the step contract, and the three questions it had to answer

Built 22 August 2026, on top of S0 and S1. The plan's own words for this step: *an input the
driver composes, an executor, and an output the driver validates.* What follows is what that
turned into, and where it departs from the plan.

## What exists now

| Piece | Where | What it holds |
|---|---|---|
| the contract | `steps/contract.py` | declared fields; one declaration is rendered into the input **and** checks what comes back |
| the definition | `steps/definition.py` | a step is data: role, prose file, contract |
| the registry | `steps/registry.py` | a name means one definition; an unknown name is refused when the run is created, not when it runs |
| the method | `method/` | prose the driver encloses, shipped inside the wheel |
| the executor | `driver/executor.py` | the driver hands over an input and is given raw text back. That is the whole of what it knows about an agent |
| the runner | `driver/runner.py` | compose, execute, validate, record — with the retry policy |
| the fake | `providers/fake/` | an executor with no CLI behind it, so every test runs with no provider and no network |

One declaration, two readers — the agent reads the contract as a list of fields in its input,
the program checks the same list against what came back. They cannot drift apart, because
there is only one of them.

## Question 4 — what happens when a step fails

Settled with the plan and now implemented literally: **three attempts on the role's provider,
each enclosing why the last was refused, then the fallback provider gets one, then the run
stops** naming the step, the provider and what the output was missing.

A test holds the part that matters: no two attempts are given the same input. An attempt that
repeats the input is not an attempt, it is a coin toss.

A provider that dies is an attempt like any other — `ExecutorFailed` is enclosed as the reason
and the next attempt begins. There is no nudge, and there never will be: typing "continue" at a
stuck session is a guess wearing the clothes of a recovery.

## Question 5 — the ceiling inside a step

**Answered, not built.** A step declares whether it may be split; if it may, the driver closes
the session at the ceiling and starts the next with the same input plus what the previous
produced. There is no session to run out of context until S3, so the field would land with no
reader — and rule 5 forbids that. It arrives with the thing that watches the ceiling.

## Question 6 — what the reviewer's verdict does mechanically

**Half built, deliberately.** The contract can express it: `Records` with an `Enum` severity is
in the code and the shipped `probe` step already returns findings with
`note` / `advice` / `blocking`. The *consequence* — a blocking finding makes the deliver step
refuse — needs a deliver step, and that is S4. Same rule: no field without its reader.

## Where this departs from the plan

The plan draws a step directory flat: `input.md`, `output.json`, `raw.txt`, `meta.json`. That is
the one-attempt case, and the retry policy makes attempts the norm rather than the exception. A
refused attempt has to stay readable without re-running the night, so:

```
steps/<n>-<name>/
  attempt-<k>/  input.md  raw.txt  meta.json  refusal.txt
  output.json   the output that satisfied the contract
  meta.json     which attempt produced it, on which provider
```

The plan's four files are still there; they moved one level down, and the accepted output stayed
at the top where the next step's driver looks for it.

## The step the kit ships

`probe` — report what you can see from here: the branch, whether the tree can be written to, and
anything a longer job would trip over. It exists for two readers. Today it is what makes S2
demonstrable end to end. At S3 it is the top rung of `agent-kit provider check`: *a one-shot job
returns something*, measured rather than claimed.

The four steps of a feature — design, build, verify, deliver — are S4's, with their prose and
their contracts. Until then `DEFAULT_STEPS` names only what the kit can actually run, because a
default naming steps that do not exist is exactly the defect the measurement found.
