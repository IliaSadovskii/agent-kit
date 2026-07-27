# Writing Plans

Turn an approved spec into an executable implementation plan. Save it to
`docs/plans/YYYY-MM-DD-<feature-name>.md`.

A plan is the complete task specification handed over up front — goal, constraints, file
boundaries, and how each piece is verified. It is not a transcript of the implementation: don't
pre-write the code the Build step will write. Give the implementer everything needed to make good
decisions, then let them make those decisions.

If the spec covers several independent subsystems, split it into one plan per subsystem, each
producing working, testable software on its own.

## Plan document

```markdown
# [Feature Name] Implementation Plan

**Goal:** [one sentence — what this builds]

**Architecture:** [2-3 sentences — the approach and why]

**Tech stack:** [key technologies and libraries]

## Global constraints

[The spec's project-wide requirements — version floors, dependency limits, naming and copy rules,
platform requirements — one line each, exact values copied verbatim from the spec. Every task
inherits this section, plus `.agent-kit/engine.md`, `.agent-kit/project/instructions.md`, and the
project's registered coding standards.]

## File map

[Which files are created or modified, and what each is responsible for. This is where the
decomposition decisions get locked in.]
```

Design units with clear boundaries: one responsibility per file, files that change together living
together, split by responsibility rather than by technical layer. In an existing codebase follow
established patterns — if it uses large files, don't unilaterally restructure, but splitting a file
you are already modifying is reasonable.

## Tasks

A task is the smallest unit that carries its own verification and is worth a fresh reviewer's gate.
Fold setup, configuration, and documentation into the task whose deliverable needs them; split only
where a reviewer could reject one task while approving its neighbor. Each task ends with an
independently testable deliverable.

```markdown
### Task N: [Component name]

**Files:** create / modify (with line ranges) / test — exact paths.

**Interfaces:**
- Consumes: [exact signatures this task uses from earlier tasks]
- Produces: [exact names, parameter and return types later tasks rely on — the implementer sees
  only their own task, so this block is how they learn the neighboring vocabulary]

**Behavior:** [what this task must make true, specifically enough to be checked]

**Verification:** [the project's real test command for this task, and what passing looks like]
```

Work test-first where the behavior is testable, and commit each completed task.

## What makes a plan fail

- Vague requirements standing in for decisions: "TBD", "handle edge cases", "add validation",
  "add appropriate error handling". Decide, and write what you decided.
- "Similar to Task N" — the implementer may read tasks out of order. Say it again.
- Types, functions, or methods referenced but defined in no task.
- Names that drift between tasks: `clearItems()` in Task 3 and `clearAllItems()` in Task 7 is a bug
  you are shipping into the implementation.

## Handoff

There is no plan-approval gate — the design approval during brainstorming was the last one. Save
the plan and hand back to `ship`, which continues autonomously per
`.agent-kit/rules/autonomous-mode.md`.

<!-- Adapted from Superpowers by Jesse Vincent (MIT). Sub-skill references localized to the /ship
     pipeline; the literal-code-per-step format dropped in favour of a specification handoff. -->
