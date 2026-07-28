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

## Decisions: three groups, never mixed

Every presentation that involves decisions separates them into exactly three groups:

- **Your call** — only the forks where different answers produce materially different work. Each
  fork: the options, a one-line trade-off per option, and your recommendation marked as such.
- **Taken as given** — decisions with an obviously better answer, being made now. Declared, one line
  each, not asked. The owner vetoes by replying; silence is consent.
- **Left to the build** — decisions that are not being made now and will be made without the owner
  once the interactive part closes. One line each: the decision, and the default you expect to take.
  Not asked either — listed, so the owner can pull any of them back while they are still cheap. A
  handful of lines; a long list is not thoroughness, it means the feature is not understood yet.

The sorting test between the first two: if the owner picking differently would genuinely surprise
you, the decision belongs in *taken as given*. Moving an obvious decision into *your call* is not
caution — it spends the owner's attention buying nothing, and trains them to skim the section where
real forks live.

The test for the third: a decision that is expensive to reverse never belongs in *left to the
build*. If it is expensive and you are confident, declare it in *taken as given* where a veto is one
word; if it is expensive and you are not, it is a *your call* fork. What is left is the cheap
remainder — and listing it is what stops the owner discovering it as an assumption in a pull
request.

## Questions

- **A question must change the work.** If every answer leads to the same change, don't ask it. If
  the environment can answer it — code, docs, git history — look it up instead.
- **Silence has a price too.** The rule above prunes; it is not a reason to arrive with nothing. A
  decision that is expensive to reverse — a data migration, the shape of a public interface,
  behavior the user will see, a boundary another feature is about to build on — is asked even when
  you hold a confident default, because after the gate closes it is settled by you alone. Cheap to
  reverse and you are confident: declare it. Expensive: ask, and say what you would do.
- **Ask about this codebase, not about software in general.** Every question names the concrete
  thing it is about — the existing behavior, the file, the current shape — and offers options that
  fit it: "orders currently expire on the nightly job; should a reset follow that or expire on
  read?" A question that would read the same in any project ("how should errors be handled?") is a
  sign the exploration has not happened yet. Go and look, then ask what is genuinely still open.
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
6. **Left to the build** — what stays open past this gate, with the default for each.
7. **Verification** — seams and layers in a few bullets, with the tooling gap if there is one.

Approval is then one round, not a section-by-section walkthrough: the owner answers the *your call*
forks and says go, or pushes back on any part — a *taken as given* line, or a *left to the build*
line they would rather settle now.

A feature the owner marked as deep is the exception, and takes two rounds rather than one: the
first settles the shape — the approach, the boundaries, the forks that reshape everything
downstream — and only once it is chosen does the second go into the mechanics inside it, where the
questions are worth asking because they now have one context instead of three. The split is about
order, not volume — the dependency-chain rule applied to a feature large enough that half the detail
questions would have been moot in the first round. What raises the volume is the depth itself, and
the owner asked for it.
