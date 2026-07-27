# Brainstorming — designs and specs

Turn an idea into a design and a spec through dialogue, then hand off to `writing-plans`. This is
the technical layer: how to build it. If `ideate` ran first, the product scope is already agreed —
build on it rather than reopening it.

Design approval is the final interactive gate of the feature flow. Present a design and get
approval before writing implementation code, including on features that look too simple to need one
— that is where unexamined assumptions cost the most. The design itself can be three sentences.

## Steps

1. **Load context** — `.agent-kit/project/manifest.yml` and the `sources` documents it registers
   (roadmap, product spec, architecture, coding standards), `.agent-kit/project/instructions.md`,
   the current code, and recent commits. Take paths from the manifest.
2. **Judge how well this feature is already specified.** Does the roadmap or spec say enough to
   build it well — what it does, how the user interacts with it, when it is done, which constraints
   apply? If it is thin, say so and go deeper into behavior and success criteria before proposing
   anything. If it is rich, confirm quickly; don't manufacture questions the docs already answer.
   This sets the depth of everything below.
3. **Ask clarifying questions, one per message.** Resolve ambiguity now, while the user is here —
   every decision left open becomes an autonomous default later, logged in the PR's Assumptions.
4. **Propose 2–3 approaches** with trade-offs, leading with your recommendation and why.
5. **Present the design and get explicit approval.** Scale each section to its complexity and ask
   after each whether it looks right. Cover architecture, components, data flow, error handling,
   and testing.
6. **Write the spec** to `docs/specs/YYYY-MM-DD-<topic>-design.md` and commit it. Prose in the
   user's language; code, paths, and identifiers in English.
7. **Invoke `writing-plans`.** That is the terminal step — no other skill, and no further gate.

## Two things worth catching early

If the request spans several independent subsystems, say so immediately and help decompose it
rather than refining details of something that needs splitting first. Each sub-project gets its own
spec, plan, and implementation cycle.

In an existing codebase, explore the structure before proposing changes and follow its patterns.
Where existing code genuinely blocks the work — a file grown unwieldy, tangled responsibilities —
include a targeted improvement, the way a good developer improves code they are working in. Don't
propose unrelated refactoring.

<!-- Adapted from Superpowers by Jesse Vincent (MIT). Visual browser companion removed (needs a
     local node server, useless in cloud). Separate spec-review gate removed so the flow has a
     single interactive checkpoint: design approval. -->
