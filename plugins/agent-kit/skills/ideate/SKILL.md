---
name: ideate
description: Think about what to build and why — generate ideas, argue them out, and land the decisions. Invoked by riff in its broad scope and by ship's Ideate step for one chosen feature; builds nothing either way.
---

# Ideate — product thinking before design

Think about *what* to build and why. Architecture and code belong to `brainstorming`, later.

Two scopes, same skill:

- **Broad** (`/agent-kit:riff`) — no feature chosen yet. Generate widely across the product, spar over the
  ideas, and put the survivors on the roadmap. Builds nothing.
- **Feature** (the `Ideate` step of `ship`) — one feature already chosen. Ask whether it is the best
  version of itself, agree what is in and out, and hand the locked scope to design.

The user is present throughout. Propose and argue; don't pick a direction and run with it. Put
everything to them in the shape `${CLAUDE_PLUGIN_ROOT}/rules/presenting.md` prescribes: verdicts
and options as compact tables or structured choices, decisions sorted into its three groups — *your
call*, *taken as given*, *left to the build* — no walls of text.

## Steps

1. **Load context** — `.agent-kit/project/manifest.yml`, then the `sources` documents it registers
   (idea, roadmap, product spec) and what already exists in the code. Take paths from the manifest.
   The product's north star lives in `sources.idea`; every idea is judged against it.

   Then check what you read against the code. A roadmap describes the product as it was last written
   down, and the part of it this riff touches may already be built, built differently, or quietly
   dropped. Verify the claims this riff leans on — only those — and where a document and the code
   disagree, put the divergence up as a fact instead of reasoning on top of it. Ideas generated
   against a product that no longer exists are exactly the ones that feel beside the point.
2. **Frame the arena** — broad scope: the theme from `$ARGUMENTS`, or ask in one message what to
   riff on. Feature scope: state what the feature is meant to do as written, and the underlying
   user need it serves. The need matters more than the wording — that is where better ideas come
   from.
3. **Check proportionality** — if the feature is trivial and there is genuinely nothing to improve,
   say so in a sentence and hand straight to design. Don't manufacture ideas to look busy. The
   feature's depth decides how readily this off-ramp is taken — `brainstorming` defines the levels,
   `sprint` and `ship` set them: `light` takes it easily, `deep` does not take it at all. The owner
   asked for the discussion, and the product layer is where its cheapest version happens, before a
   single decision has been designed against.
4. **Generate** — work the lenses below for concrete, specific ideas. Broad scope goes wide;
   feature scope stays bounded to this feature and its immediate neighbours. Hold judgment here.
5. **Spar** — now judge. State each idea's best version before assessing it, give a verdict with a
   concrete reason, and calibrate your confidence. Get genuinely behind what earns it; drop what
   doesn't with a plain "I'd cut this, because…". Follow the user's counter-arguments where they
   are good.
6. **Land the decisions** —
   - Broad: sort into keep (roadmap-worthy now), park (interesting, not yet), and cut (with the
     one-line reason, so it is not re-litigated).
   - Feature: lock what is in this feature and what is deferred. That scope is the input to design.
7. **Write survivors to the roadmap** — with the user's explicit go-ahead, append to
   `sources.roadmap` as short bullets phrased as user value. Add; never reorder or rewrite what is
   already there. Nothing is written without a yes.
8. **Hand off** — broad scope stops here and names the command to start the chosen work. Feature
   scope summarizes the locked product decisions in a few bullets and invokes `brainstorming`,
   which owns the spec.

## Lenses

Prompts for generation, not a form: the job the user actually needs done; what makes a standout
version rather than a rote one; radical simplicity — the cut that keeps the value; differentiation
a competitor could not copy easily; retention, growth, and monetization where they fit the
product's own stance; adjacent bets worth noting but not cramming in; and reframing, when the
problem itself is stated wrong.

Two things are cheap to get wrong. "Cooler" has to mean more valuable, not more ornament. And an
idea outside the current scope belongs on the roadmap, not in this feature — defer over cram.
