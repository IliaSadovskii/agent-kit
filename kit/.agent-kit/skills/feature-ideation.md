# Feature Ideation — Product Brainstorm Before Design

> **LANGUAGE: talk to the user in the language from `.agent-kit/project/manifest.yml` → `language`.**
> These instructions are English; your messages to the user follow that language.

The roadmap is a **starting point, not gospel**. Because we build the product incrementally,
every feature is a chance to stop and ask: *is this the best version of this feature, or are we
just building it because it was written down?* This step thinks at the **product / business
layer** — WHAT to build and why — one level ABOVE the design step, which handles the technical
HOW. Keep the two separate: here there is **no code, no architecture, no technical approaches**.

## When this runs

- The **Ideate** step of `ship`, right after the task is chosen, before the **Design** step
  (`brainstorming`).
- **On by default.** Skip it entirely when `ship` is called with `--no-ideate`, or when the
  user declines in the conversation ("build it as written in the roadmap"). When skipped, go
  straight to Design with the roadmap's scope unchanged.
- This step is **interactive** — the user is present. It is NOT autonomous. Do not invent a
  scope for the user; propose and let them choose.

## What this is NOT

- NOT the design step. No components, data flow, patterns, or code — that is `brainstorming`.
- NOT unbounded scope creep. The goal is a *better-considered* feature, not a bigger one.
  When in doubt, prefer **deferring an idea to the roadmap** over cramming it in now.
- NOT for gold-plating. "Cooler" must mean **more valuable to the user**, not more ornament.
  YAGNI still applies.

## Checklist

Create a task per item and complete them in order:

1. **Load product context** — read `.agent-kit/project/manifest.yml` and the `sources` docs (idea /
   product-spec, roadmap), recent commits, and what already exists. Understand the product's
   north star from `sources.idea` — every proposal must serve it, not drift into unrelated
   features.
2. **Frame the feature's intent** — state, in one or two sentences, what THIS feature is meant
   to do as written, and the underlying **user need** it serves. The need matters more than the
   literal wording — that is where better ideas come from.
3. **Proportionality check** — if the feature is trivial (a copy tweak, a config flag, a tiny
   fix) and there is genuinely nothing to improve, say so in one sentence and hand straight to
   Design. Do NOT manufacture ideas to look busy.
4. **Generate proposals across the lenses** (below) — 3–6 concrete, specific ideas. Each with:
   what it is, why it is better/simpler/more valuable, a rough sense of cost, and your
   recommendation (fold-in now / defer to roadmap / skip).
5. **Present and decide with the user** — show the proposals grouped and concise, each with
   your recommendation. Ask the user to react: accept some, reject some, or add their own. The
   user may also say "build as written" → record that and skip to Design.
6. **Lock the product scope** — write down what is IN this feature now and what is
   OUT / deferred. This agreed scope is the input to the Design step.
7. **Capture deferred ideas** — for any adjacent feature the user liked but that is out of this
   feature's scope, OFFER to append it to the roadmap (`sources.roadmap`) as a short backlog
   bullet, so it is not lost. Only write to the roadmap if the user agrees.
8. **Hand off to Design** — summarize the locked product decisions briefly (a few bullets) so
   the `brainstorming` step and the spec can reference them. Do NOT write a separate spec file
   here — Design owns the spec. Then invoke the Design step.

## The lenses

Run the feature through these angles — they are prompts for ideas, not a form to fill:

- **Better / cooler** — is there a more valuable or more delightful way to meet the underlying
  need? What separates a standout version from a rote implementation?
- **Simpler (YAGNI)** — can we deliver the same value with less? Cut or defer parts that are
  not pulling their weight.
- **Fold in now** — small extra settings, options, or functionality that are **cheap to add
  now but expensive to retrofit later** (a config flag, an obvious adjacent option, an
  extensibility seam the product will clearly want). Only when genuinely cheap and valuable.
- **Adjacent business features** — nearby features this one naturally connects to. For each:
  build now (only if small, high-value, and in the spirit of the current scope) or **defer →
  add to the roadmap**.
- **Reframe** — sometimes the roadmap's framing of the feature is itself suboptimal. If so,
  propose a different framing of the problem, not just the solution.

## Handoff

The outcome of this step is a short set of **product decisions** (scope IN / OUT, chosen
improvements, deferred-to-roadmap items) — not a spec. Feed it into the Design step
(`brainstorming`), which turns the agreed scope into a technical design and writes the spec in
`docs/specs/`. Deferred adjacent features go to the roadmap (with the user's OK).

## Key principles

- **Product layer only** — WHAT and why; leave HOW to Design.
- **Serve the north star** — proposals must advance the product idea, not sprawl.
- **Propose, don't impose** — the user picks; you recommend.
- **Defer over cram** — a great idea outside this scope belongs in the roadmap, not this PR.
- **Proportional effort** — a rich feature gets real ideation; a trivial one gets a sentence.
- **YAGNI ruthlessly** — cooler means more valuable, never more gold-plating.
