---
name: brainstorming
description: Turn a chosen feature into an approved technical design and a written spec. Invoked by ship's Design step, or when the user explicitly asks to design something — explore the codebase, resolve ambiguity, compare real alternatives, get explicit approval, then hand off to writing-plans.
---

# Brainstorming — designs and specs

Turn an idea into a design and a spec through dialogue, then hand off to `writing-plans`. This is
the technical layer: how to build it. If `ideate` ran first, the product scope is already agreed —
build on it rather than reopening it.

Design approval is the final interactive gate of the feature flow. Present a design and get approval
before writing implementation code, including on features that look too simple to need one — that is
where unexamined assumptions cost the most. The design itself can be three sentences.

## Steps

1. **Load context** — `.agent-kit/project/manifest.yml` and the `sources` documents it registers
   (roadmap, product spec, architecture, coding standards), `.agent-kit/project/instructions.md`,
   the current code, and recent commits. Take paths from the manifest.
2. **Explore the codebase before proposing anything.** Scale the effort to the feature:
   - *Small or well-understood change* — read the relevant files yourself. Delegation would cost
     more than it returns.
   - *Anything touching unfamiliar code, several subsystems, or an established pattern you have not
     seen* — send 2–3 `Explore` agents concurrently in a single message, each on a different angle:
     features similar to this one and how they are implemented; the architecture and abstractions of
     the area being changed; the conventions the change has to live inside — testing approach, error
     handling, extension points. Ask each to end with the 5–10 files most worth reading, then read
     those files yourself. The agents locate the code; the understanding has to be yours, because
     you are the one designing against it.
3. **Judge how well this feature is already specified.** Does the roadmap or spec say enough to
   build it well — what it does, how the user interacts with it, when it is done, which constraints
   apply? If it is thin, say so and go deeper into behavior and success criteria before proposing
   anything. If it is rich, confirm quickly; don't manufacture questions the docs already answer.
   This sets the depth of everything below.
4. **Resolve every ambiguity now.** This is the step that decides the quality of the run: the user
   is here, and after approval every open decision becomes an autonomous default logged in the PR's
   Assumptions. Cover edge cases, error handling, integration points, scope boundaries, backward
   compatibility, and performance expectations.

   How to ask is governed by `${CLAUDE_PLUGIN_ROOT}/rules/presenting.md`: only questions whose
   answer changes the work, facts looked up rather than asked, independent decisions batched into
   one structured round, dependency chains sequenced shape-changer first, and a recommendation on
   every question. Decisions with an obviously better answer are not questions at all — they go into
   the design's *taken as given* section.

   Depth follows step 3: press hard where the answers are genuinely open, and move fast where the
   documents already settled them. Thoroughness is not the same thing as an interrogation.
5. **Compare real alternatives, not variations on one idea.** Produce 2–3 approaches with genuinely
   different trade-offs — the smallest change that reuses what exists, the clean structure you would
   choose with no legacy, and the pragmatic middle. On a substantial feature, generate them
   concurrently with one `Plan` agent per approach, each given only its own mandate, so they do not
   converge on the same answer; on a small one, write them yourself. Then form your own opinion and
   present the trade-offs as the alternatives table from the presenting rule, recommendation marked.
6. **Decide how this feature will be proven.** See below. This is part of the design, not an
   afterthought at the end of the build.
7. **Present the design and get explicit approval.** One screen, in the order the presenting rule
   gives: goal, diagram, alternatives table, *your call*, *taken as given*, verification. Approval
   is one round, not a section-by-section walkthrough — the owner answers the open forks and says
   go, or pushes back on any part. Architecture, components, data flow, and error handling live in
   the diagram and the decision lines, not in paragraphs.
8. **Write the spec** to `docs/specs/YYYY-MM-DD-<topic>-design.md` and commit it, including the
   verification plan and the resolved decisions from both sections. Diagrams go in as Mermaid —
   GitHub renders them. Prose in the user's language; code, paths, and identifiers in English.
9. **Invoke `writing-plans`.** That is the terminal step — no other skill, and no further gate.

## The verification plan

After approval nobody is watching, so what the tests can prove is the only thing standing between
the design and a merged mistake. Decide three things while the owner is still here.

**The seams.** Name the points this feature will be tested at, before deciding what to test. Prefer
seams the project already has to new ones, take the highest seam that can still see the behavior,
and keep the count as low as the feature allows — one is the ideal. Tests written at low seams
multiply, ossify the implementation, and are the reason suites get abandoned. Check the seams with
the owner: this is where their expectations and yours diverge most cheaply.

**The layers.** Which kinds of test this feature actually needs — the `agent-kit:tester` agent holds
the catalogue, from static analysis through contract and end-to-end. Choose deliberately and say
what you are leaving out. A backend change with a frontend consumer almost always needs a contract
test; a pure refactor may need nothing new at all.

**The tooling gap.** Compare what those layers require against what
`.agent-kit/project/instructions.md` says the project has. Anything missing — an end-to-end runner,
a browser driver, a container for a real database, a mutation-testing tool, a coverage reporter —
gets named here, with what it buys and what it costs to run.

Then say plainly which side of the line it falls on:

- **The session can install it** — say so, and it happens during the build, with the install added to
  the project's `scripts/cloud-setup.sh` so the next session and CI have it too. Never install
  something the owner has not seen in this plan; that is exactly what this step is for.
- **The session cannot** — a paid service, a credential, a device, something needing their machine —
  it becomes a recorded manual action, and you state here what will go unproven until they do it,
  so the gap is a decision rather than a surprise.

If the honest answer is that this feature cannot be verified well without something the owner has to
provide, say that now, in the design, and let them choose. Discovering it after approval turns it
into an assumption buried in a pull request.

## Two things worth catching early

If the request spans several independent subsystems, say so immediately and help decompose it rather
than refining details of something that needs splitting first. Each sub-project gets its own spec,
plan, and implementation cycle.

In an existing codebase follow the patterns the exploration found. Where existing code genuinely
blocks the work — a file grown unwieldy, tangled responsibilities — include a targeted improvement,
the way a good developer improves code they are working in. Don't propose unrelated refactoring.
