# Writing Plans

> **LANGUAGE: messages to the user and the plan's prose follow `.agent-kit/project/manifest.yml` →
> `language`** (engine rule, `.agent-kit/engine.md`). Code, paths, commands, identifiers are in English.
> These skill instructions are in English, but the conversation and plan text follow the
> user's language.

## Overview

Write comprehensive implementation plans assuming the engineer has zero context for our codebase and questionable taste. Document everything they need to know: which files to touch for each task, code, testing, docs they might need to check, how to test it. Give them the whole plan as bite-sized tasks. DRY. YAGNI. Frequent commits.

Assume they are a skilled developer, but know almost nothing about our toolset or problem domain. Assume they don't know good test design very well.

**Announce at start:** "I'm using the writing-plans skill to create the implementation plan."

**Save plans to:** `docs/plans/YYYY-MM-DD-<feature-name>.md`

## Scope Check

If the spec covers multiple independent subsystems, it should have been broken into sub-project specs during brainstorming. If it wasn't, suggest breaking this into separate plans — one per subsystem. Each plan should produce working, testable software on its own.

## File Structure

Before defining tasks, map out which files will be created or modified and what each one is responsible for. This is where decomposition decisions get locked in.

- Design units with clear boundaries and well-defined interfaces. Each file should have one clear
  responsibility (see the coding standards registered in the manifest).
- You reason best about code you can hold in context at once, and edits are more reliable when files are focused. Prefer smaller, focused files over large ones that do too much.
- Files that change together should live together. Split by responsibility, not by technical layer.
- In existing codebases, follow established patterns. If the codebase uses large files, don't unilaterally restructure - but if a file you're modifying has grown unwieldy, including a split in the plan is reasonable.

This structure informs the task decomposition. Each task should produce self-contained changes that make sense independently.

## Task Right-Sizing

A task is the smallest unit that carries its own test cycle and is worth a
fresh reviewer's gate. When drawing task boundaries: fold setup,
configuration, scaffolding, and documentation steps into the task whose
deliverable needs them; split only where a reviewer could meaningfully
reject one task while approving its neighbor. Each task ends with an
independently testable deliverable.

## Bite-Sized Task Granularity

**Each step is one action (2-5 minutes):**
- "Write the failing test" - step
- "Run it to make sure it fails" - step
- "Implement the minimal code to make the test pass" - step
- "Run the tests and make sure they pass" - step
- "Commit" - step

## Plan Document Header

**Every plan MUST start with this header:**

```markdown
# [Feature Name] Implementation Plan

> **Execution:** implement task-by-task following the `ship` pipeline (defined in
> `.agent-kit/workflows/ship.md`). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** [One sentence describing what this builds]

**Architecture:** [2-3 sentences about approach]

**Tech Stack:** [Key technologies/libraries]

## Global Constraints

[The spec's project-wide requirements — version floors, dependency limits,
naming and copy rules, platform requirements — one line each, with exact
values copied verbatim from the spec. Every task's requirements implicitly
include this section, plus `.agent-kit/engine.md`, `.agent-kit/project/instructions.md`, and the project's
registered coding standards.]

---
```

## Task Structure

The example below shows the *shape* of a task — it is stack-neutral. Write every step in the
project's actual language, file layout, test framework, and commands (real code, not the
placeholders shown here).

````markdown
### Task N: [Component Name]

**Files:**
- Create: `exact/path/to/file.<ext>`
- Modify: `exact/path/to/existing.<ext>:123-145`
- Test: `exact/path/to/test-file`

**Interfaces:**
- Consumes: [what this task uses from earlier tasks — exact signatures]
- Produces: [what later tasks rely on — exact function names, parameter
  and return types. A task's implementer sees only their own task; this
  block is how they learn the names and types neighboring tasks use.]

- [ ] **Step 1: Write the failing test**

[the failing test, in the project's test framework — asserts the specific behavior, real code]

- [ ] **Step 2: Run test to verify it fails**

Run: `<the project's test command, filtered to this test>`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

[actual code, in the project's language]

- [ ] **Step 4: Run test to verify it passes**

Run: `<the project's test command, filtered to this test>`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add <files>
git commit -m "feat: add specific feature"
```
````

## No Placeholders

Every step must contain the actual content an engineer needs. These are **plan failures** — never write them:
- "TBD", "TODO", "implement later", "fill in details"
- "Add appropriate error handling" / "add validation" / "handle edge cases"
- "Write tests for the above" (without actual test code)
- "Similar to Task N" (repeat the code — the engineer may be reading tasks out of order)
- Steps that describe what to do without showing how (code blocks required for code steps)
- References to types, functions, or methods not defined in any task

## Remember
- Exact file paths always
- Complete code in every step — if a step changes code, show the code
- Exact commands with expected output
- DRY, YAGNI, frequent commits, docblocks on classes/public methods

## Self-Review

After writing the complete plan, look at the spec with fresh eyes and check the plan against it.
This is a checklist you run yourself — not a subagent dispatch. An INDEPENDENT pass by the
`plan-reviewer` subagent follows in Ship; your self-review is the cheap first filter, not a replacement.

**1. Spec coverage:** Skim each section/requirement in the spec. Can you point to a task that implements it? List any gaps.

**2. Placeholder scan:** Search your plan for red flags — any of the patterns from the "No Placeholders" section above. Fix them.

**3. Type consistency:** Do the types, method signatures, and property names you used in later tasks match what you defined in earlier tasks? A method called `clearItems()` in Task 3 but `clearAllItems()` in Task 7 is a bug.

If you find issues, fix them inline. No need to re-review — just fix and move on. If you find a spec requirement with no task, add the task.

## Execution Handoff

**No plan-approval gate.** Do NOT stop to ask the user to read or approve the plan.
The final interactive checkpoint in the flow was the design approval during brainstorming
(the `Task` choice and the optional `Ideate` brainstorm came before it). After the
self-review, the flow continues autonomously — there is no user gate here.

After saving the plan, hand back to `ship`: the `Plan review` step runs an INDEPENDENT
`plan-reviewer` over the spec + plan (fix its critical/major findings before any code), then the
remaining steps run autonomously per `.agent-kit/workflows/ship.md` and
`.agent-kit/rules/autonomous-mode.md`, on a branch following the active provider adapter. The PR
gets an Assumptions section; do NOT merge — merge is the owner's
decision.

<!-- Adapted from Superpowers by Jesse Vincent (MIT). superpowers: sub-skill
     references localized to this project's /ship pipeline. -->
