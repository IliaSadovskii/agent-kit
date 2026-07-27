---
name: writing-plans
description: Turn an approved spec into an executable implementation plan with a file map, task boundaries, and per-task verification. Invoked after design approval and before any implementation — normally by brainstorming's final step.
---

# Writing Plans

Turn an approved spec into an implementation plan at `docs/plans/YYYY-MM-DD-<feature-name>.md`.

A plan is the task specification handed over up front: goal, constraints, file boundaries, and how
each piece is verified. It is not a transcript of the implementation — don't pre-write the code the
Build step will write. Give the implementer what they need to make good decisions, then let them
make those decisions.

If the spec covers several independent subsystems, write one plan per subsystem, each producing
working software on its own.

## Shape

```markdown
# [Feature] Implementation Plan

**Goal:** one sentence — what this builds.
**Architecture:** two or three sentences — the approach and why.
**Tech stack:** the key technologies and libraries.

## Global constraints

The spec's project-wide requirements — version floors, dependency limits, naming and copy rules,
platform requirements — one line each, values copied verbatim from the spec. Every task inherits
this section, plus the always-on governance, the project instructions, and the coding standards.

## File map

Which files are created or modified, and what each is responsible for.

### Task N: [Component]

**Files:** create / modify (with line ranges) / test — exact paths.
**Interfaces:** what this task consumes from earlier ones, and the exact names and types later
tasks rely on. The implementer sees only their own task; this is how they learn the vocabulary.
**Behavior:** what this task must make true, specifically enough to be checked.
**Verification:** the seam this task is tested at and the layers it needs, taken from the spec's
verification plan; the project's real command to run them; and what passing looks like. If the task
needs tooling the project does not have yet, name it here — the Test step installs it.

## Run log

Empty at planning time. The build appends assumptions, deviations, skipped layers, and manual
actions here as they happen — the `ship` pipeline owns the rules and assembles the PR from it.
```

The file map is where decomposition gets locked in: one responsibility per file, files that change
together living together, split by responsibility rather than by technical layer. In an existing
codebase follow established patterns — splitting a file you are already modifying is reasonable,
unilaterally restructuring is not.

A task is the smallest unit that carries its own verification. Fold setup and configuration into
the task whose deliverable needs them; split only where a reviewer could reject one task while
approving its neighbor. Work test-first where the behavior is testable, and commit each completed
task.

## What makes a plan fail

- Vague requirements standing in for decisions — "TBD", "handle edge cases", "add validation".
  Decide, and write down what you decided.
- "Similar to Task N". The implementer may read tasks out of order; say it again.
- Types, functions, or methods referenced but defined in no task.
- Names that drift between tasks: `clearItems()` in Task 3 and `clearAllItems()` in Task 7 is a bug
  you are shipping into the implementation.

## Handoff

There is no plan-approval gate — design approval was the last one. Save the plan and hand back to
`ship`, which continues autonomously per `${CLAUDE_PLUGIN_ROOT}/rules/autonomous-mode.md`.
