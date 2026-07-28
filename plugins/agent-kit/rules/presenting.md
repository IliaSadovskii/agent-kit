# Presenting to the owner (flow rule)

Applies whenever a pipeline puts something in front of the owner — a question during ideation, a
design for approval, a set of options, a brief. The owner's attention is the scarcest resource in
the pipeline: everything presented must be readable in one pass and decidable in seconds. A design
the owner skims because it is a wall of text gets a worse approval than a shorter one they actually
read.

## The shape of anything presented

- **One screen per subject.** A feature's design presentation fits on one terminal screen. If it
  does not, cut detail until it does — the spec file holds the rest.
- **Structure before prose.** Reach for a diagram, a table, or a list before a paragraph. Prose is
  for arguments; everything enumerable gets a shape the eye can scan.
- **Diagrams where there is structure.** A flow, a pipeline, a component boundary — draw it. In
  terminal output use box-drawing/ASCII, which renders everywhere. In files that land on GitHub —
  specs, PR descriptions — use Mermaid, which GitHub renders.
- **Air.** Blank lines between blocks. Three short blocks read faster than one dense one.

## Decisions: two sections, never mixed

Every presentation that involves decisions separates them into exactly two groups:

- **Your call** — only the forks where different answers produce materially different work. Each
  fork: the options, a one-line trade-off per option, and your recommendation marked as such.
- **Taken as given** — decisions with an obviously better answer. Declared, one line each, not
  asked. The owner vetoes by replying; silence is consent.

The sorting test: if the owner picking differently would genuinely surprise you, the decision
belongs in *taken as given*. Moving an obvious decision into *your call* is not caution — it spends
the owner's attention buying nothing, and trains them to skim the section where real forks live.

## Questions

- **A question must change the work.** If every answer leads to the same change, don't ask it. If
  the environment can answer it — code, docs, git history — look it up instead.
- **Batch independent decisions into one structured round.** When the session has a structured
  question tool (AskUserQuestion), use it: several decisions, each with options and a marked
  recommendation, answered in one interaction. Serial free-text questions are the expensive
  fallback, not the default.
- **Never batch a dependency chain.** A question whose answer could moot or reshape another in the
  same batch goes in a later round. Settle the shape-changing decision first; half the remaining
  questions stop needing to be asked.
- **Every question carries a recommendation** with a one-sentence reason. A question with no
  proposed answer offloads the work onto the owner. If they answer "whatever you think", state your
  choice and get explicit confirmation rather than silently deciding.

## The design presentation

The design put up for approval (brainstorming's presentation step) follows this order, each part
present only when the feature gives it content:

1. **Goal** — one line.
2. **Diagram** — the flow or structure the change introduces or alters.
3. **Alternatives** — a compact table (approach / what it buys / what it costs), recommendation
   marked. Only when real alternatives were on the table.
4. **Your call** — the open forks, per the rules above.
5. **Taken as given** — the declared decisions.
6. **Verification** — seams and layers in a few bullets, with the tooling gap if there is one.

Approval is then one round, not a section-by-section walkthrough: the owner answers the *your call*
forks and says go, or pushes back on any part, including a *taken as given* line.
