---
name: brainstorming
description: Turn a chosen feature into an approved technical design and a written spec. Use before implementing any feature — explore the codebase, resolve ambiguity, compare real alternatives, get explicit approval, then hand off to writing-plans.
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
4. **Resolve every ambiguity now, one question per message.** This is the step that decides the
   quality of the run: the user is here, and after approval every open decision becomes an
   autonomous default logged in the PR's Assumptions. Cover edge cases, error handling, integration
   points, scope boundaries, backward compatibility, and performance expectations.

   Three rules make this step worth the user's time rather than a tax on it:

   - **Ask about decisions, not facts.** Anything the environment can answer — the test framework,
     how an existing endpoint behaves, whether a column is nullable — you look up. What you put to
     the user is what only they can decide, because it depends on intent rather than on state.
     Spending a question on something you could have read is how an interview loses its authority.
   - **Follow the dependency order, not the checklist order.** Decisions unlock and moot each other:
     settle the one that changes the shape of the others first, and half the list stops needing to
     be asked. Walk each branch to its end before opening the next one.
   - **Carry your own recommendation into every question,** with the reasoning in a sentence. A
     question with no proposed answer offloads the work onto the user. If they say "whatever you
     think is best", state your choice and get explicit confirmation rather than silently deciding.

   Depth follows step 3: press hard where the answers are genuinely open, and move fast where the
   documents already settled them. Thoroughness is not the same thing as an interrogation.
5. **Compare real alternatives, not variations on one idea.** Produce 2–3 approaches with genuinely
   different trade-offs — the smallest change that reuses what exists, the clean structure you would
   choose with no legacy, and the pragmatic middle. On a substantial feature, generate them
   concurrently with one `Plan` agent per approach, each given only its own mandate, so they do not
   converge on the same answer; on a small one, write them yourself. Then form your own opinion and
   present the trade-offs, leading with your recommendation and why.
6. **Present the design and get explicit approval.** Scale each section to its complexity and ask
   after each whether it looks right. Cover architecture, components, data flow, error handling, and
   testing.
7. **Write the spec** to `docs/specs/YYYY-MM-DD-<topic>-design.md` and commit it. Prose in the
   user's language; code, paths, and identifiers in English.
8. **Invoke `writing-plans`.** That is the terminal step — no other skill, and no further gate.

## Two things worth catching early

If the request spans several independent subsystems, say so immediately and help decompose it rather
than refining details of something that needs splitting first. Each sub-project gets its own spec,
plan, and implementation cycle.

In an existing codebase follow the patterns the exploration found. Where existing code genuinely
blocks the work — a file grown unwieldy, tangled responsibilities — include a targeted improvement,
the way a good developer improves code they are working in. Don't propose unrelated refactoring.

<!-- The dialogue and spec handoff are adapted from Superpowers by Jesse Vincent (MIT); see
     NOTICE.md. The facts-versus-decisions rule and the dependency ordering of questions in step 4
     come from the `grilling` skill by Matt Pocock (MIT). The codebase-exploration and
     competing-architecture steps follow Anthropic's
     feature-dev plugin, using Claude Code's built-in Explore and Plan agents rather than shipping
     duplicates of them. The visual browser companion was dropped (needs a local node server,
     useless in cloud) and the separate spec-review gate removed, so the flow keeps a single
     interactive checkpoint: design approval. -->
