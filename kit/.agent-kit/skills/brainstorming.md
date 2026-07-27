# Brainstorming Ideas Into Designs

Turn an idea into a design and a spec through collaborative dialogue, then hand off to
`writing-plans`. This is the technical layer — how to build it. If `feature-ideation` ran before
this, the product scope is already agreed; build on it rather than reopening it.

Design approval is the final interactive gate of the feature flow (`.agent-kit/engine.md`). Present
a design and get approval before writing implementation code — including on projects that look too
simple to need one, where unexamined assumptions cost the most. The design itself can be three
sentences when the feature is genuinely small.

## Flow

1. **Load context** — `.agent-kit/project/manifest.yml` and the `sources` documents it registers
   (roadmap, product spec, architecture, coding standards), `.agent-kit/project/instructions.md`,
   and recent commits. Take paths from the manifest; never hardcode `docs/…`.
2. **Judge how well this feature is already specified** — see below. This sets the depth of
   everything after it.
3. **Ask clarifying questions**, one per message.
4. **Propose 2–3 approaches** with trade-offs, leading with your recommendation and why.
5. **Present the design and get explicit approval.**
6. **Write the spec** to `docs/specs/YYYY-MM-DD-<topic>-design.md` and commit it.
7. **Invoke `writing-plans`.** That is the terminal step — no other skill, and no further gate.

## How well is this feature specified?

The manifest guarantees the project is bootstrapped; the specific next feature may be described
richly or barely. Judge whether the roadmap and spec say enough to build it well: what it does, how
the user interacts with it, when it is done, which constraints and edge cases apply.

- **Thin** — say so honestly, then go deeper: explore the feature's behavior, UX, and success
  criteria before proposing approaches.
- **Rich** — confirm the design quickly and move on. Don't manufacture questions the docs already
  answer.

## Asking

- Check the current state of the code before asking about it.
- If the request spans several independent subsystems, say so immediately and help decompose it
  into sub-projects rather than refining details of something that needs splitting first. Each
  sub-project gets its own spec, plan, and implementation cycle.
- One question per message; multiple choice when it fits, open-ended when it doesn't.
- Resolve ambiguity now, while the user is here. Every decision left open becomes an autonomous
  default later, logged in the PR's Assumptions.

## Presenting the design

Scale each section to its complexity — a sentence when it is straightforward, a few hundred words
when it is genuinely nuanced. Ask after each section whether it looks right. Cover architecture,
components, data flow, error handling, and testing.

Break the system into units with one clear purpose, communicating through defined interfaces, each
understandable and testable on its own. For each, you should be able to say what it does, how it is
used, and what it depends on. If someone cannot understand a unit without reading its internals, or
its internals cannot change without breaking consumers, the boundaries need work.

In an existing codebase, explore the current structure first and follow its patterns. Where
existing code genuinely blocks the work — a file that has grown unwieldy, tangled responsibilities
— include a targeted improvement, the way a good developer improves code they are working in. Don't
propose unrelated refactoring.

## The spec

Write the approved design to `docs/specs/YYYY-MM-DD-<topic>-design.md` and commit it. It is prose
in the user's language; code, paths, and identifiers stay English. Then invoke `writing-plans`
directly — there is no spec-approval gate.

<!-- Adapted from Superpowers by Jesse Vincent (MIT). Visual browser companion removed (needs a
     local node server, useless in cloud). Separate spec-review gate removed so the flow has a
     single interactive checkpoint: design approval. -->
