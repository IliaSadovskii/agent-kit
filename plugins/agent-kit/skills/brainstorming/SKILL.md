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

   One angle is not optional at either size: **who else depends on what this change touches.** Find
   the callers, the subscribers, and the stored data of every surface being altered — find-references
   answers this in one call where a name search takes five — and work out whether the change alters
   what any of them sees. A feature that quietly moves a neighbour's behavior is the most expensive
   thing an unattended run can produce, and the owner is the only one who knows whether that
   neighbour was meant to move.
3. **Check the documents against the code, then judge what they leave open.** A document was true
   when it was written; the code is what runs. Verify the claims this feature leans on — only those,
   not the document as a whole — and where the two disagree, the divergence is not yours to resolve
   silently: put it up as a fact. *The spec says X, the code does Y — which is right?* The answer
   often changes the feature, and it is a question the owner can answer in seconds.

   Unchecked stale documents are the main reason a design's questions land as strange: the reasoning
   is sound and the ground under it is three months old. Note each divergence for the `docs` command
   as well, so it is repaired rather than rediscovered next time.

   Then judge what is genuinely left open: does the roadmap or spec still say enough to build this
   well — what it does, how the user interacts with it, when it is done, which constraints apply? If
   it is thin, go deeper into behavior and success criteria before proposing anything. If it is rich
   and the code agrees with it, confirm quickly rather than manufacturing questions it already
   answers.
4. **Resolve every ambiguity now.** This is the step that decides the quality of the run: the user
   is here, and after approval every open decision becomes an autonomous default logged in the PR's
   Assumptions.

   **Sweep first, then cut.** A design that arrives with two questions has usually not been filtered
   hard — it has skipped the enumeration, and a question taken off the top of the head reads as
   random because it is. So before asking anything, walk the axes below and write down every
   candidate. This list is working material and is never shown:

   - **States and transitions** — what this thing can be in, and what moves it between them.
   - **The unhappy paths** — empty, missing, duplicate, out of order, concurrent, partial failure,
     retry, timeout.
   - **Data over time** — what is stored, what has to migrate, what happens to the rows that already
     exist.
   - **Permissions and boundaries** — who may do this, what changes for who may not, what crosses a
     trust boundary.
   - **The behavior it alters** — what someone relying on how it works today would notice.
   - **The neighbours** from step 2 — whose expectations move, and whether that was intended.
   - **The edge of the feature** — the adjacent thing a reasonable person would assume is included
     and is not, or the reverse.
   - **Scale and cost** — the volumes, sizes, and frequencies this has to hold up at, and what
     should happen when it does not.
   - **Reversibility** — which of these would be expensive to undo once built and shipped.

   Then cut hard, by `${CLAUDE_PLUGIN_ROOT}/rules/presenting.md`: only questions whose answer changes
   the work, facts looked up rather than asked, each one named against the concrete code rather than
   software in general, independent decisions batched into one structured round, dependency chains
   sequenced shape-changer first, and a recommendation on every question. Most of the sweep dies
   here, and that is the point — the survivors are the ones you could not answer yourself.

   The reversibility axis decides what survives the cut. Expensive to undo goes to the owner even
   when you hold a confident default; cheap and confident is declared in *taken as given*; cheap and
   still open is listed in *left to the build* with the default you will take. Between the sweep and
   those three groups, nothing quietly disappears — which is what lets the filter stay strict
   without the design going shallow.

   How much of this the feature earns is the depth dial below. Thoroughness is not the same thing as
   an interrogation.
5. **Ask the ecosystem before designing from scratch.** On a feature of substance, check whether
   this is a problem the stack already solved whole: first the dependencies the project has
   installed, then the ecosystem the coding standards' library map points into. A found solution
   is not an automatic yes — it becomes one of the alternatives in the next step, compared on the
   same trade-off table, with the always-on proportionality rule deciding whether taking it is
   right. Skip the scan when the feature is plainly this product's own domain logic; that is
   exactly what should be written by hand.
6. **Compare real alternatives, not variations on one idea.** Produce 2–3 approaches with genuinely
   different trade-offs — the smallest change that reuses what exists, the clean structure you would
   choose with no legacy, and the pragmatic middle; when the ecosystem scan found a ready-made
   solution, adopting it is one of them. On a substantial feature, generate them concurrently with
   one `Plan` agent per approach, each given only its own mandate, so they do not converge on the
   same answer; on a small one, write them yourself. Then form your own opinion and present the
   trade-offs as the alternatives table from the presenting rule, recommendation marked. Whatever
   wins, the design names the stance the coding standards record for the area it changes — that
   table has a row per area, so take the row, not the whole document — and stays inside it.
7. **Decide how this feature will be proven.** See below. This is part of the design, not an
   afterthought at the end of the build.
8. **Present the design and get explicit approval.** One screen, in the order the presenting rule
   gives: goal, diagram, alternatives table, *your call*, *taken as given*, *left to the build*,
   verification. Approval is one round — two on a deep feature, shape then mechanics, per the same
   rule — and not a section-by-section walkthrough: the owner answers the open forks and says go, or
   pushes back on any part, including a line they would rather settle now than leave to the build.
   Architecture, components, data flow, and error handling live in the diagram and the decision
   lines, not in paragraphs.
9. **Write the spec** — unless the run is under `ship --brief`, where an approved sketch is already
   the spec and is copied into place by the caller; adding a second document there is the defect this
   exception exists to prevent. Otherwise to `docs/specs/YYYY-MM-DD-<topic>-design.md` and commit it, including the
   verification plan and the resolved decisions from all three sections — what was left open and
   its default is part of the record, not a loose end. Diagrams go in as Mermaid —
   GitHub renders them. Prose in the user's language; code, paths, and identifiers in English.
10. **Invoke `writing-plans`.** That is the terminal step — no other skill, and no further gate.

## Depth

How much of the owner's attention this design is worth is a decision, and it is made before the
design starts rather than discovered halfway through it.

- **light** — a small, well-understood change. The sweep still runs; most of it dies at the cut. The
  design can be three sentences and a verification line.
- **normal** — the default. Everything above, one approval round.
- **deep** — a feature large enough, or expensive enough to get wrong, that the owner wants the
  detail discussed. Two rounds, shape then mechanics. The internal mechanics a normal feature settles
  silently — the shape of a state machine, where a boundary sits, what a failure does to the rest of
  the flow — are legitimate material here, and this is the one place a question may be asked because
  the answer is genuinely hard rather than because it is expensive to reverse.

`sprint` records the level per feature during its brief; `ship` takes `--deep` and `--quick`. With
nothing given, judge it from the feature and state your choice in one line before you start asking,
so the owner can move it — guessing low skims something expensive, guessing high spends attention
they did not want to spend, and both are cheap to correct if you say the level out loud.

Depth raises how much detail is worth a question. It never lowers the filter: a question whose
answers all lead to the same work is not asked at any level.

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
