# Changelog

All notable changes to the kit. Versions follow semver from the perspective of a project that
installed it — see [docs/developing.md](docs/developing.md#versioning).

## 0.15.1

A pipeline's named delegations stop being negotiable.

- **`reviewer` and `tester` are steps, not judgment calls.** The baseline's advice on subagents was
  written entirely as restraint — they cost context, don't spawn one for small work, keep the count
  low — and never said that a delegation a pipeline names by name is that step rather than an option.
  Two of three headless `ship --brief` runs in one sprint skipped Review and Test on that reading
  while a third ran them; nothing in the kit's text made the third one right.
- **A host instruction against spawning agents is about initiative, not about a requested step.** A
  session may arrive carrying one. Typing the command is the request, so it does not reach the
  pipeline's own delegations — and doing the review inline instead is not a substitute, since the
  point is that the reviewer did not write the code.
- **A delegation that cannot run is said out loud** — named, with the reason, in the run log and the
  PR. Skipping one in silence produces a feature that looks reviewed and is not.

## 0.15.0

The always-on governance gains the one rule it was missing: keep the diff surgical.

- **Only what the request needs changes.** No reformatting, no reworded comments, no improving the
  code you happened to open on the way, and the surrounding style is matched even where you would
  have written it differently — style drift is what makes a diff unreadable for whoever reviews it.
- **Orphans are split from dead code.** An import, variable, or function that nothing calls *because
  of this change* is cleaned up; code that was already dead is named and left for the owner. Until
  now the baseline said only that the best change often removes code, which pulled the other way.
- **A finished diff has a test.** Every changed line traces back to the request — the author-side
  counterpart to the `reviewer` agent's scope check, which until now was the only place this was
  looked for, and only after the code was written.

Adapted from the Karpathy-Inspired Claude Code Guidelines; see the plugin's `NOTICE.md` for what was
taken and what was deliberately not.

## 0.14.0

The playbook stops interviewing the owner about architecture and starts showing them what it
concluded.

- **Nothing about architecture is asked any more.** Each area's stance is derived from two sources
  the skill already had: what the code does, and what the stack is understood to do well, researched
  from the framework's own documentation and the ecosystem's catalogues rather than recalled. The
  research step now runs before the stances that depend on it.
- **The skill closes by putting its conclusions up.** One screen — stack profile, the stance table,
  the library map's picks, the testing idioms, and any place the code and the stack's practice
  disagreed, each with what was done about it — followed by an invitation to add what only the owner
  knows. An owner reacting to a finished playbook remembers what they care about; the same person
  facing a blank architecture question at bootstrap does not, which is what the old interview asked
  them to do.
- **Silence is consent.** No answer leaves the playbook as written, so an owner who does not care
  pays one screen and nothing else. What they do add is written in as their rule, in their words,
  and preserved by later refreshes. Headless runs ask nothing and send the summary to the run record.
- **The refresh asks nothing either.** A stance the code has parted from, and a new area with no row
  yet, are reported in its one-line note instead of interrupting a feature with a question.
- **`idea-interview` stops asking the same thing in other words.** "Which conventions are real, and
  which are legacy you would rather not spread" is the playbook's close-out question, asked once,
  where there is something concrete on screen to answer against.

## 0.13.0

The architecture stance stops being one question with one answer.

- **A project gets a stance per area, not a stance.** The domain, the HTTP surface, background work,
  the client, how data is reached — a project answers the architecture question separately wherever
  its answer actually differs, and asking for a single global one forced everything after it through
  a wrong frame. A CRUD app still has one line; a layered product has three or four. The areas are
  derived from the application type and from what the codebase already separates, never from a
  checklist — inventing areas a project does not have is the failure mode, because each line becomes
  a rule someone obeys forever.
- **The question is where to deviate, not what to choose.** The framework's own idiom holds
  everywhere the owner does not depart from it, so the round asks about departures and their cost.
  Nobody answers "choose an architecture" well at bootstrap, before the code that would inform the
  answer exists; everyone can answer "here is where I would leave the framework's path, and why".
  Areas where the default is plainly right are declared rather than asked.
- **The playbook records a table, looked up by area.** `brainstorming` names the stance for the area
  its feature changes and designs inside that row; `reviewer` checks against the same row. A feature
  touching the HTTP surface no longer reads a paragraph about the whole product to find its rule.
- **A refresh may ask exactly one question**: the project grew an area the table has no row for. It
  still never changes a recorded stance, and it still reports, by area, where the code has parted
  from what the table says.

## 0.12.0

0.11.0 fixed the presenting rule, and two skills that ask the owner questions did not notice: they
carried a hand-copied fragment of the rule instead of pointing at it.

- **`stack-playbook` and `idea-interview` now defer to the rule** rather than restating a piece of
  it, so they pick up the counterweight, the codebase-grounded questions, and the three decision
  groups — and the next fix to the rule as well.
- **The architecture stance is asked with its consequences attached.** It is the most expensive
  decision the kit ever records and every later feature inherits it, yet it was one question
  answerable in one word, leaving the agent to invent where boundaries sit and what a module is.
  The concrete reading of the stance for this repo now goes up together with the question. Derived
  without the owner, it is marked `derived` and surfaced where the run's decisions are read — the
  PR's Assumptions, the sprint report — instead of only in a log.
- **A refresh reports a stance the code stopped following.** It still never changes the stance, but
  where the boundaries in the document are no longer the boundaries in the code it says so in one
  line. Which of the two is wrong is the owner's call, and they cannot make it while nobody tells
  them the two parted.
- **`ideate` checks the roadmap against the code** before generating, for the claims the riff leans
  on. Ideas argued against a product that was last written down six months ago are the ones that
  feel beside the point.
- **Depth reaches the product layer.** `ideate`'s proportionality off-ramp is taken readily on a
  `light` feature and not at all on a `deep` one — the owner asked for the discussion, and the
  product layer is where its cheapest version happens.

## 0.11.0

Design conversations stop being thin. Every rule in the kit pushed one way — spend less of the
owner's attention — and with no counterweight the pipelines settled into asking two shallow
questions and calling the design agreed.

- **The sweep before the cut.** `brainstorming` now enumerates candidate questions across fixed axes
  — states and transitions, unhappy paths, data over time, permissions and boundaries, altered
  behavior, neighbours, the edge of the feature, scale, reversibility — and only then applies the
  filter. Too few questions was never a strict filter; it was an enumeration that never happened, and
  a question picked off the top of the head is exactly the one that reads as random.
- **Silence has a price too.** A decision expensive to reverse — a migration, a public interface,
  visible behavior, a boundary the next feature builds on — is now put to the owner even when the
  design holds a confident default, because after the gate it is settled alone. The pruning rule
  stays; it stops doubling as an excuse to arrive with nothing.
- **Questions name this codebase.** A question that would read the same in any project is treated as
  evidence the exploration has not happened yet, not as a question.
- **Documents are checked against the code.** Only the claims a feature leans on, and a divergence is
  put up as a fact — *the spec says X, the code does Y* — rather than resolved silently. Stale
  documents are the main reason sound reasoning produces odd questions.
- **Neighbours are found before anything is proposed.** Callers, subscribers, and stored data of
  every surface being altered, and whether what they see changes. An unattended run moving a
  neighbour's behavior is the most expensive thing it can do.
- **A third decision group: *left to the build*.** What stays open past the gate, each line with the
  default that will be taken, so the owner can pull any of it back while it is still cheap instead of
  meeting it as an assumption in a pull request. Autonomous mode treats those defaults as answers.
- **Depth is chosen, not guessed.** `light` / `normal` / `deep` per feature — `sprint` agrees it when
  the batch is composed and records it in `queue.yml`, `ship` takes `--deep` and `--quick`, and with
  neither the level is judged and stated in one line so it can be moved. A `deep` feature gets two
  rounds, shape then mechanics, and its internal mechanics become fair game for questions.
- **The sprint brief loses its clock.** The hour of attention and the ten minutes per feature are
  gone; the brief ends when nothing expensive to reverse is still open. A batch of small features
  takes minutes, one turning on a migration takes as long as that decision takes.

## 0.10.0

A sprint stops being a stack of pull requests the owner has to merge in the right order, and becomes
one pull request that either lands the batch or does not.

- **The batch is delivered by an integration PR.** Stacked feature PRs target their parent's branch,
  so their merge button moves code sideways rather than into the default branch — merge them in the
  wrong order, or with a squash, and the sprint quietly fails to land. The run now ends by branching
  `sprint/<slug>-integration` off a freshly pulled `main`, merging the feature tips into it,
  resolving conflicts between features there, and running the project's full suite on that tree —
  the only tree that matches what `main` will contain, and one no feature PR had ever been checked
  in. That branch's pull request is the sprint's single mergeable one. It asks to be merged with a
  merge commit rather than a squash, and the run checks once that the repository allows it.
- **Feature PRs become drafts.** They keep doing what they were good at — a narrow diff to read,
  a place for review comments, its own CI — and stop pretending to be a way to land code. The rule
  is conditional on the base branch, so it applies to any pull request opened against another
  feature's branch, and `sprint` verifies it as a backstop when a headless child does not.
- **`--integrate <feature ids>` takes the batch in parts**, for an owner who wants two features in
  production before committing to the rest. A batch must be closed under dependencies — a feature
  ships with its ancestors, whose branches carry its commits — and a later batch needs nothing done
  to the feature branches: it is built from the new `main` the same way. The same rebuild covers a
  review round through `/agent-kit:address` and a `main` that moved underneath an open batch.
- **Branches are swept, not remembered.** A branch whose `git diff origin/main...<branch>` is empty
  adds nothing to `main` and is deleted locally and on the remote, its pull request closed with a
  line naming the integration PR that carried it. The test errs one way only: a branch still holding
  unlanded code never reads as empty. It runs at the end of a run and in the next sprint's preflight.

## 0.9.0

The kit learns to draw the app. A project's screens stop being a thing you hold in your head and
become a picture the agent keeps true.

- **New skill: `screens`** — every screen of the app as a wireframe card, every transition as a
  labelled arrow, in one self-contained HTML file that opens with no server and no network. Built
  from the project's own documents and code: what the code has is `implemented` and points at the
  file that implements it, what only the documents promise is `planned`. Later runs **reconcile
  rather than regenerate** — ids are never reused, so a screen number stays a stable address for
  as long as the project lives. The viewer ranks screens by their transitions, left to right:
  a screen's column is the longest path to it, so entry screens stand at the left, every step
  forward points right, and a back edge is routed under the ranks it spans. `flow` groups screens
  where that costs no crossings; it does not place them. A project with no screens — a library, a
  CLI — gets one sentence and no map.
- **New skill: `screens-riff`** — the map shows what the app is; this asks what it should become,
  and answers in the same picture. Ideas arrive as one structured round; taken ones land as `idea`
  cards next to what already exists, turned-down ones stay as `rejected` memory so the same
  proposal never costs the owner attention twice, and "not now" is a third verdict that writes
  nothing. Improvements that are not screen-shaped go in the written review, never on the map.
- **A screen id is a unit of work.** `/agent-kit:ship S7` resolves against the map — the card's
  title, purpose, layout, and transitions seed the task. And `docs-reflection` treats the map as a
  living document: a feature that changed what the app shows flips statuses and adds what it
  introduced, in the feature's own PR, because an `implemented` card points at code that exists
  only there.
- **One file crosses the ownership line on purpose.** The viewer is plugin code that lives in the
  project's `docs/`, and later runs replace it — otherwise viewer improvements would never reach a
  project that already generated a map. The rule and its single exception are written down in
  `docs/developing.md`, the file says so in its own header, and the validator fails if that marker
  disappears. The map beside it, `screens.data.js`, belongs to the project.
- **`sprint` no longer talks about the night.** The command was written as an evening brief, a
  night of building, and a morning report; nothing in the design needs the hour, only that the run
  is unattended. Same steps, time-neutral wording — start a sprint over a working afternoon if
  that is when you have the hour.
- **The validator grew teeth for the payload's JavaScript**: it is parsed, the demo map is loaded
  the way the viewer loads it, a page's `<script src>` must ship beside it, any `sources.<key>` the
  payload reads must exist in the manifest template, and the demo map must obey the counter and
  code-path rules it teaches.

## 0.8.0

The kit learns to run a night shift: one evening hour of the owner's attention becomes a batch of
features built while they sleep.

- **New skill: `sprint`** — an evening brief, a night of ship runs, a morning report. The brief
  composes a coherent batch of 3–6 features with an explicit dependency order, scopes them in one
  pass, and sketches each design in about ten minutes of owner attention; approved specs land in
  `.agent-kit/sprint/`. The run executes each feature as `ship --brief` in its own fresh headless
  session, one at a time so dependent features can stack — each builds on its parent's *branch*,
  and nothing is ever merged without the owner. The night closes with an integration check over
  every stack tip and a one-screen report led by the decisions taken without the owner.
- **`ship --brief <spec>`** — a ship run with no interactive gates, for a design sketch the owner
  already approved. Deviations follow a ladder: implementation mechanics are the run's to choose, a
  settled approach that cannot work as written is replaced and recorded, and product scope is never
  changed silently. A sibling `upstream.md` tells the run what actually happened to the features it
  builds on, as opposed to what the sketch imagined.
- **New skill: `stack-playbook`** — the agent knows where it is and asks the ecosystem first. It
  detects the stack from dependency manifests and lockfiles, mines the codebase for the house
  conventions, records the owner's architecture stance, and researches the installed framework's
  idioms and library map from the ecosystem's own sources — training-data knowledge of an ecosystem
  is stale by definition. The result is short justified rules written into the registered
  coding-standards document, ending with a fingerprint of the manifests it was generated from.
  `ship` checks that fingerprint at the head of every run: current is silent, missing triggers a
  full generation, stale refreshes only what drifted — never the stance, which changes only on the
  owner's word.
- **The presenting rule** (`rules/presenting.md`) now governs everything put in front of the owner:
  one screen per subject, structure before prose, decisions split into *your call* and *taken as
  given*, questions batched with a marked recommendation each.
- **PR descriptions are scannable** — verdict first, evidence collapsed.

## 0.7.1

Found while running the kit on a real project: with the `code-review` plugin installed, a feature was
reviewing its own diff in three waves — `agent-kit:reviewer`, up to three `pr-review-toolkit`
specialists, and then the plugin's own dozen agents in the PR step. 0.7.0 added the third wave without
reconciling it against the first two.

The Review step now branches on whether the plugin is reachable, splitting by responsibility rather
than piling on depth:

- **Plugin available** — `agent-kit:reviewer` covers only what nothing else can, whether the diff is
  the feature that was approved. The bug hunt belongs to the PR step, where the plugin's five
  independent reviewers and its confidence-scoring pass do it better. The `pr-review-toolkit`
  specialists stop being a default and become an escalation for a change that earns a specific lens.
- **Plugin absent** — unchanged from 0.7.0: the reviewer carries correctness too, and the specialists
  are worth spawning, because nothing downstream will look again.

One wave either way. The step also states the agent budget out loud — roughly one reviewer here, a
dozen in the PR step — so the next person to add a tier has to notice the total first.

## 0.7.0

One install gets everything. 0.6.1 and 0.6.2 taught the kit to *use* Anthropic's `code-review` and
`pr-review-toolkit`; this makes them arrive on their own.

- **The kit declares both as dependencies.** `/plugin install agent-kit@agent-kit` now resolves and
  installs them too, and Claude Code lists what it added at the end of the install. Nothing to
  install by hand, and no per-project step.
- Cross-marketplace dependencies are blocked by default, and the allowlist that unblocks them belongs
  to the marketplace the user installs *from* — this one. `marketplace.json` now carries
  `allowCrossMarketplaceDependenciesOn: ["claude-plugins-official"]`. Without it the install fails
  outright, so the validator refuses to ship a cross-marketplace dependency whose source is not
  allowlisted.
- No version constraints on either dependency: those resolve against git tags in someone else's
  repository, so pinning would break the moment their tagging convention differed.
- If the dependencies cannot be reached at all — an organization policy blocking the official
  marketplace, or a Claude Code old enough not to ship it — they are left unresolved and the kit
  still runs. Every step that uses them is written "when enabled", and the `reviewer` agent covers
  correctness alone. You lose depth, not the pipeline.

## 0.6.2

Follow-up audit of the same class of bug as 0.6.1: an instruction the agent cannot act on.

- **Plugin agents and commands carry their plugin's name**, and 0.6.1 wrote them bare. Delegating to
  `silent-failure-hunter` resolves to nothing; `pr-review-toolkit:silent-failure-hunter` is the real
  name. Same for the review pass on the open PR, now spelled `/code-review:code-review`.
- The README gives the two install commands and says the official marketplace is already configured,
  so nobody has to work out where these plugins come from.

Audited and found sound, no change needed: the kit's own five pipelines are user-invoked and its five
internal skills are not, so pipelines can call them; `/security-review`, `/simplify`, and `/run` are
model-invocable, unlike `/code-review` and `/verify`; the `gh` and CI steps already degrade when the
session cannot reach them; and the guard hook asks on `git push origin main`, `git push --force`, and
`gh pr merge` while staying silent on `git status`, `echo "git push --force"`, and a push of
`claude/main-fix`.

## 0.6.1

The kit's main review path never ran. Found in real use, not by the validator.

Claude Code's bundled `/code-review` and `/verify` are marked `disable-model-invocation` — a property
of those skills, not a session setting, so no agent in any session can start them. The kit wrote both
into pipelines as the primary path, which meant:

- `ship`'s Review step fell through to its fallback line every time; the real reviewer was the
  fallback and the documented path was decoration.
- `ship`'s Test step nominally confirmed the running app through `/verify`.
- **`fix`'s Review step did nothing at all** — `/code-review` was its only reviewer, with no
  fallback beneath it. `debug` inherited that through "continue through the tail of `fix`".
- Worst of it: the `reviewer` agent was instructed *not* to hunt for bugs because "`/code-review`
  already does that". Nothing did.

Fixed by making every path something an agent can actually reach:

- **`agent-kit:reviewer` is the primary reviewer** in `ship` and `fix`, and covers correctness as
  well as design conformance. It gained a Correctness lens, and two lenses borrowed from what the
  bundled review does and the kit had no answer for: **History** (`git blame`/`git log -L` over the
  replaced lines, so a "cleanup" does not delete a guard added on purpose) and **Settled elsewhere**
  (review comments on the PRs that last touched these files — conventions the project agreed to
  without writing down).
- **Plugin commands and agents *are* model-invocable**, unlike their bundled equivalents. So the
  Review step now escalates through `pr-review-toolkit`'s specialists when a project has that plugin
  enabled, and the PR step runs the official `code-review` plugin's command on the open pull request
  — same multi-agent, confidence-scored architecture as the bundled version, reachable by an agent.
  Both optional; the kit works without them.
- **The Test step drives the app with the project's own commands.**
- **The bundled pair is offered, not invoked.** The PR description's Review section ends with
  `/code-review` and `/verify` as commands the owner can copy — the only way they get offered at all,
  and the owner is reading it at the moment a keystroke is cheap. `ship` explicitly must not stop and
  wait for them: after design approval the owner may be asleep, and a pipeline that waits for a human
  never finishes.

## 0.6.0

Two carriers for guarantees the kit could previously only phrase as prose: the project's CI, and a
permission gate in front of the commands the governance forbids. Nothing for an installed project
to migrate; the CI bullet applies at the next bootstrap or `--rebootstrap`.

### CI, detect-first

CI is the only verifier that outlives a session — everything the run proves locally dies with it,
and 0.5.0 taught `ship` to watch `gh pr checks` without ensuring there was anything to watch. CI
now gets the same treatment as the author's docs:

- Bootstrap detects an existing workflow and registers it in the manifest (`sources.ci`) instead
  of generating a second one. Where the declared Verification layers and the workflow disagree,
  that is a finding for the owner, never an edit.
- On a repository with no CI, it proposes a workflow running the Verification commands from the
  project instructions verbatim, written only on an explicit yes.
- When `ship`'s Test step installs new tooling, it extends a workflow the kit generated or the
  owner approved; a CI the project brought with it is not the kit's to edit — that gap goes to the
  Run log as a manual action.

### The guard hook

The rules the governance states as "never" — merge a pull request, push the default branch,
force-push — were promises. A new PreToolUse hook turns them into a confirmation: a matching
command comes back as an explicit permission question instead of running. The decision is "ask",
never "deny" — interactively the owner confirms in one click; in an unattended autonomous run
nobody answers, so the command does not run, which is exactly what the rules promised. Parsing
lives in `guard.py` and judges each pipeline segment on its own words, so `echo "git push"` or a
push of `claude/main-fix` does not cry wolf — a guard that does teaches everyone to click through
it. Everything that is judgment rather than invariant stays prose.

## 0.5.0

The run survives its own length, and the pipeline no longer ends the moment the PR opens. Nothing
for an installed project to migrate.

### The run log

Assumptions and manual actions used to exist only "in the PR" — which is written at the end of a
run long enough to outlive its own context, so a decision taken in hour three could be gone before
the PR step came to record it.

- The plan now ends with a `## Run log` section, appended to and committed as decisions happen:
  assumptions, deviations from the approved design, skipped verification layers, owner-only work,
  the tester's skipped-layer report.
- The PR's Assumptions and Manual actions are assembled from it rather than from memory, and a
  resumed or compacted session picks the run's state up from disk instead of losing it.

### After the PR

- **`ship`'s PR step now includes CI.** A red pipeline is part of the step, not the owner's
  problem: check `gh pr checks` after opening, fix in-scope failures, rerun the verification the
  fix put at risk, push again.
- **New command `/agent-kit:address`** closes a review round on an open PR: collect the owner's
  comments and the CI status, sort them out loud — in scope, design change, out of scope — fix,
  rerun what the fixes put at risk, push, and answer every thread. An owner comment that asks for
  a design change counts as the new approval; only contradicting comments are a question.

### Fixed

- The marketplace description still advertised `review`, `test`, and infrastructure provisioning,
  all removed in 0.4.0. It now mirrors `plugin.json`, and the validator keeps the two identical.
- `riff` and `docs` did not say what to do on a project with no manifest; both now handle it
  instead of reading null sources.
- `ship`'s `/verify` step gained the fallback the other delegated tools already had: no `/verify`
  in the session means starting the app with the project's own commands, not skipping the check.
- The `reviewer` agent no longer assumes the default branch is named `main`.
- `fix` states its interaction contract: no design gate, user presumed nearby, ask only when a
  real ambiguity changes what gets built.

### Smaller

- `idea-interview` batches independent facts into one message of up to four questions and keeps
  one-at-a-time only for decisions that depend on each other.
- `scripts/cloud-setup.sh` is now required to check before installing and no-op in seconds when
  everything is present — it runs at every session start, local ones included — and the hook
  carries an explicit 600-second timeout for the first, slow run.
- `docs-reflection` closes the learning loop: a review finding that traced back to an unwritten
  rule is a missing line in the coding standards, and a gap in the project instructions is
  proposed in the PR description rather than silently repeated next feature.
- The internal skills describe themselves as invoked by the pipelines rather than as "use when…"
  triggers, so plain conversation no longer competes with the engine's rule that free text is
  never routed into a pipeline.

## 0.4.1

Housekeeping on the payload. No new behavior, nothing for an installed project to do.

- **`/simplify` moved from the Test step to Review.** It is a quality pass, not a test; it sat
  between running the suite and checking the suite, and it edits the diff after the suite has run.
  It is now gated on a diff large enough to be worth reading through, and framed as what it does —
  readability, not a third opinion on correctness. Running it made the Review step's own "do not add
  a third opinion" line false, which is fixed.
- **Dropped `ship`'s restatement of "prove each test can fail".** The `tester` agent performs it and
  documents it; restating a subagent's job in the caller is the scaffolding that causes
  over-verification. The flake rule, which was genuinely new, folded into the suite step.
- **The two review passes are stated as independent** and may run concurrently.
- **Removed history and design commentary from the payload.** Provenance comments recording which
  sub-skill references were localized, that a browser companion was dropped, that a spec-review gate
  was removed, and that a code-per-step format was replaced — eleven lines telling the model what
  the kit used to be. `NOTICE.md` carries the MIT attribution and remains intact. Also gone: the
  kit explaining its own economics mid-instruction, `engine.md` describing itself, and
  `idea-interview` referencing its own steps by number, which breaks the moment they are renumbered.

## 0.4.0

The kit is a Claude Code plugin, it delegates the steps Claude Code now does better than a
hand-written prompt, and it is cut back to what it was actually for. See
[migrations/0.4.0.md](migrations/0.4.0.md) for what an installed project has to do.

### Reuse over reinvention

The kit said "prefer framework primitives and existing dependencies" and left it there. That is a
statement of preference; it never asked anyone to go and look, which is why hand-rolled helpers get
written — by someone who did not check.

- **New always-on section, "Reaching for what already exists"**: search for the behavior before
  writing it, search by behavior rather than by the name you would have chosen, and prefer in order
  the language, the framework, an installed dependency, a maintained library, and only then your own
  code. It states when a new dependency is the right call (well-defined, long-solved problems — dates,
  money, parsing, retries, crypto) and when it is not, and asks for the reasoning out loud rather
  than a silent `package.json` edit. Being always-on, it applies to `fix`, `debug`, and plain
  terminal work too, not only to `ship`.
- `ship`'s Build step points at it and at language-server tooling, since find-references is what
  makes the search actually succeed.
- **The `reviewer` agent gained two lenses**: *silent failure* — swallowed errors, over-broad catch
  blocks, and fallbacks the user never learns about, which survive both the suite and a bug hunt
  because nothing is red — and *reinvention*, which names the existing helper when it finds one.
- The plugin README now points at language servers and at `pr-review-toolkit` as worthwhile
  companions, and says plainly why writing tests is not delegated the way review and security are:
  everything the kit hands off inspects finished work, and authoring tests means writing code inside
  one project's conventions and seams.

### Verification

The target moved from "the tests pass" to "someone can merge this without reading the diff".

- **How a feature will be proven is now decided at design time**, as part of the design the owner
  approves, rather than improvised after the build. The new verification plan in `brainstorming`
  fixes three things while the owner is still present: the **seams** the feature is tested at
  (prefer existing ones, take the highest that still sees the behavior, keep the count near one),
  the **layers** it needs, and the **tooling gap** — what has to be installed to run those layers.
- **Missing test tooling gets installed** during the build when the session can do it, added to
  `scripts/cloud-setup.sh` so later sessions and CI inherit it, and recorded in the project
  instructions. Nothing is installed that the owner did not see in the approved plan. What the
  session cannot install becomes a manual action stating what stays unproven without it.
- **The `tester` agent gained a layer catalogue** — static, unit, integration, contract, end-to-end,
  regression, property-based, snapshot, accessibility, concurrency and idempotency, performance —
  and must report which layers it deliberately skipped. Contract tests are called out specifically:
  they are where "works on the backend, broken on the frontend" lives, and they were the layer most
  often missing entirely.
- **Every new test must be proven able to fail.** Invert the condition, watch the test go red, put
  the code back. A test that passes against broken code buys confidence it has not earned, and this
  is what separates a suite you can rely on from one that merely runs. Where the project has a
  mutation-testing tool, a surviving mutant counts as an uncovered behavior.
- **A flaky test is a defect, not an annoyance.** One known flake teaches everyone to ignore red,
  and then nothing in the suite means anything. `ship` now fails its own bar on a flake instead of
  noting it.
- **`/simplify` runs in the Test step** — four parallel agents covering reuse, simplification,
  efficiency, and level of abstraction. `/code-review` finds bugs at the next step; this is the pass
  that keeps the diff worth reading.
- Static analysis is stated as a test layer rather than a formality: a type error is a failing test.
- The project instructions template gained a Verification section with one line per layer, and
  `<none yet>` as a deliberate signal for the design step to propose adding a missing one.

### Bootstrap

- **`bootstrapped` was one flag doing two jobs**, so "I know exactly what I want built" waited behind
  "first write a roadmap" — even though a free-text task already skips the only step that needs one.
  The two concerns are now separate. Technical setup (manifest, project instructions, coding
  standards, cloud-setup script) is part of any run and needs no gate; it is cheap and mostly
  detection. Product bootstrap (idea and roadmap) gates only what it actually protects: task
  selection and product scoping.
- **`ship <task>` on a project with no product docs now builds the task**, skipping Task and Ideate,
  saying out loud what it is working without, and repeating that in the pull request. It is
  deliberately not blocked and deliberately not silent — the owner sees the notice on every review
  and runs `--rebootstrap` when they have had enough. `ship` with no task is unchanged: it still
  runs the full interview and stops at a bootstrap PR.
- **`idea-interview` splits into a setup half and a product half**, so `ship` can ask for the first
  alone.
- **`idea-interview` branches on whether code already exists.** A fresh repository is interviewed
  for everything. A repository with a real codebase gets the flow inverted — read the code, README,
  and history first, bring a draft, ask the owner to correct it — and spends their attention only on
  what code cannot tell you: intent, what is deliberately out of scope, what comes next, and which
  conventions are real rather than legacy. The roadmap stays required, but covers only what is
  ahead instead of reconstructing a phasing of what already shipped.

### Scope

Nine commands became five. The kit exists for autonomous feature development, and everything that
was not that has gone.

- **Removed `/infra`, and the `infra-local` and `infra-cloud` skills** with their hosting catalog
  and mobile-env references — 333 lines, a quarter of the payload. Provisioning is interactive by
  nature, was the most stack-opinionated material in the kit (validated only on Laravel plus Expo),
  and had nothing to do with shipping a feature autonomously. It was a second product living inside
  the first.
- **Removed `/review` and `/test`.** Both had become one-line wrappers: `/code-review` is a built-in
  command you can simply type, and "cover this with tests" works as a plain request. Nothing is lost
  inside `ship`, which still runs the `reviewer` and `tester` agents at their own steps.
- **Removed `/go`.** A router over nine commands stops paying for itself at five, and it put a menu
  between the user and the work. Bootstrap is reached through `ship`, which already detects a
  missing manifest and runs the interview first.
- `manifest.yml` drops the `infrastructure` block and `sources.deployment`, and instead invites
  project-specific `sources` keys of your own.

### Distribution

- **The kit installs as a plugin**: `/plugin marketplace add IliaSadovskii/agent-kit` and
  `/plugin install agent-kit@agent-kit`. The repository is its own marketplace.
- **Removed `install.sh`, `kit-update.sh`, `kit.lock`, and the whole conflict/checksum machinery.**
  Versioning, updating, and per-file replacement are what the plugin system already does; the kit
  had rebuilt all of it by hand.
- **Removed the adapter layer.** `catalog.tsv`, `generate-adapters.py`, and the 19 generated
  wrappers under `.claude/` existed because the payload had to serve two providers. With one
  provider a wrapper that points at a canonical file is pure indirection, so each skill now *is*
  the canonical file. 88 payload files became 30.
- **Commands are namespaced**: `/ship` is now `/agent-kit:ship`, and so on for every command.
- **`engine.md` arrives through the plugin's SessionStart hook** instead of a managed block in the
  project's `CLAUDE.md`. The kit no longer writes to `CLAUDE.md` or `.claude/settings.json` at all.
- `.agent-kit/project/manifest.yml` and `instructions.md` are unchanged and stay in the project.

### Delegating to Claude Code

- **`ship`'s Review step splits in two.** `/code-review` covers correctness — a multi-agent pass
  that scores its own findings for confidence and reports only what survives, which is the
  filtering pass the kit was missing. The `reviewer` agent is rewritten around the one question
  `/code-review` cannot answer: does the diff match the design that was approved for it.
- **`ship`'s Security step names its tools** — `/security-review` first, the `claude-security`
  plugin when a project has it enabled, and an adversarial subagent only as the fallback.
- **`ship` and `test` confirm the change against the running app** with `/verify`, instead of
  treating a green suite as proof.
- **`fix` and `debug` use `/code-review` and `/security-review`** rather than their own review pass.
- **`brainstorming` explores before it proposes**, and generates competing architectures in
  parallel — the approach of Anthropic's `feature-dev` plugin, built on the `Explore` and `Plan`
  agents Claude Code already ships rather than on copies of them.
- Effort levels are now part of the instructions: reviews name the level that matches what is at
  stake instead of inheriting whatever the session had.

### Governance

- **`engine.md` is trimmed to what is genuinely always-on** — communication, working style,
  delegation, and the core rules — and stays under the 10,000-character hook output cap, which the
  validator enforces. The workflow-scoped material moved into the skills that use it.
- The always-on guidance for narration, verbosity, scope, delegation, and self-correction follows
  Anthropic's [Prompting Claude Opus 5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5)
  guidance, including its warning against stacking extra self-verification on a model that already
  verifies its own work.
- Long autonomous runs point at auto mode instead of describing a hand-rolled equivalent.

### Tooling

- `scripts/validate.sh` is rewritten for the plugin: manifest and version agreement, skill and agent
  frontmatter, dangling `${CLAUDE_PLUGIN_ROOT}` references, the engine size cap, and
  `claude plugin validate --strict` when the CLI is present. It also fails a skill whose body is
  only a pointer at another file.
- `scripts/release.sh` bumps `plugin.json` and `marketplace.json` alongside `VERSION`.

## 0.3.0

The kit targets Claude Code only. Codex support is removed rather than left to rot: it doubled
every surface — two adapter trees, two root instruction files, two description columns per catalog
row, a provider switch through the installer and both validators — while only one of them was
actually used. See [migrations/0.3.0.md](migrations/0.3.0.md) for the manual cleanup an installed
project needs.

### Removed

- The Codex payload: `.agents/skills/`, `.codex/agents/`, `AGENTS.md` and its managed block, and
  the `.codex/hooks.json` template.
- `install.sh --providers`, the `providers:` key in `kit.lock`, and the providers line in
  `install.sh status`.
- `.agent-kit/platforms/`. The provider abstraction had one implementation left; its three
  Claude-specific rules moved into `.agent-kit/engine.md`.

### Changed

- `catalog.tsv` drops the per-provider columns: `claude_desc`/`codex_desc` collapse to `desc`,
  `claude_note`/`codex_note` to `note`, and the Codex-only `sandbox` column is gone.
- `scripts/generate-adapters.py` emits only `.claude/` wrappers; the payload is 22 generated files
  instead of 41.
- Both validators check a single adapter surface. The repository validator additionally asserts
  that no Codex artefact reappears in the payload or in a fresh install.

### Changed — prompts rewritten for the Claude 5 generation

Anthropic's guidance for Claude 5 models is that prompting is mostly subtraction: rules written to
protect against older models' failure modes now cost quality, and repeating an instruction across
several files creates conflicting signals rather than reinforcement. The prompt payload shrinks
from 1671 to 929 lines — 44% — with no capability removed. What survives is mostly a sequence of
steps per command plus the domain facts each step needs, rather than instruction scaffolding.

- Every fact now lives in exactly one file. The design gate was previously restated six times
  across the engine, `ship`, `brainstorming`, `writing-plans`, and `autonomous-mode`; "never merge"
  appeared in seven. The engine owns the shared rules and the workflows stop paraphrasing them.
- Dropped the pseudo-XML guardrails (`<HARD-GATE>`, `<SINGLE-GATE>`, `<SCOPE>`,
  `<NEVER-MOVE-USER-DOCS>`, …), the caps-lock imperatives, and the "this is too simple to need a
  design" anti-pattern essay. The gate itself is unchanged — it is now stated once, plainly.
- Removed the duplicated `LANGUAGE:` preamble from six skills; the engine's communication section
  is the only place it is defined.
- **Removed the `plan-reviewer` role and the `Plan review` step**, along with the spec self-review
  and plan self-review. Claude 5 verifies its own work; instructing it to verify — and especially
  delegating verification to a subagent — produces over-verification without a capability gain.
  Verification of the finished diff still happens: `tester` and `reviewer` are unchanged in spirit,
  and `reviewer` now explicitly reports everything with a confidence level rather than
  self-filtering by severity, which was suppressing real findings.
- `writing-plans` no longer asks for the full implementation code and a five-step
  test-run-implement-run-commit ritual per task. A plan is now the task specification handed over
  up front — goal, constraints, file map, task boundaries with interfaces, and how each is verified.
- The engine gained what the guidance says to add rather than assume: how to write for a user who
  cannot see your thinking, the length of generated files, scope discipline, when a correction is
  worth making, and an explicit cap on subagent delegation (Claude 5 reaches for subagents more
  readily than its predecessors).
- Dropped the per-skill "Key principles" sections, which restated their own body in bullet form,
  and the "create a task per item" preambles, which describe what the harness already does.
- Skill descriptions are now trigger-oriented ("Use when…") rather than descriptive. That is the
  text Claude reads to decide whether a skill is relevant, and a stated trigger measurably beats a
  statement of what the skill is.

### Removed — two commands that duplicated existing steps

- **`/plan-next`** is gone. "Read the roadmap, propose 2–3 next options, stop" was already the
  `Task` step of `ship` and a row in the `/go` menu.
- **`riff` and `feature-ideation` are merged into one `ideate` skill** with a broad scope and a
  feature scope. They were two halves of the same job — 206 lines that each carried a section
  explaining how not to overlap with the other, a section that only existed because they were
  split. `/riff` still exists and now runs `ideate` in its broad scope.

### Fixed

- The PR section names `## Ручные действия` were hardcoded in Russian inside English canonical
  files. The canonical name is now "Manual actions", with translation driven by the project
  language like the rest of the PR.

## 0.2.0

First release as a standalone repository. The kit previously lived inside the project it was
developed in; the behavior is unchanged, the distribution is new.

### Added

- `install.sh` — install, update, status, diff, and uninstall, with `--dry-run`, `--ref`,
  `--from`, `--providers`, and `--force`.
- `.agent-kit/kit.lock` — records the installed version, source ref, and two checksums per file, so
  an update can tell an untouched file from one the project customized.
- `.agent-kit/scripts/kit-update.sh` — in-project update shim; no URL to remember.
- `catalog.tsv` + `scripts/generate-adapters.py` — every provider wrapper is generated from one
  authoring source, and CI fails if the payload drifts from it.
- `scripts/validate.sh` — validates the payload, performs a real install into a scratch repository,
  and asserts the update semantics (idempotent re-run, preserved local edits, untouched user files).
- Clean `templates/` for the user-owned corner: an unbootstrapped manifest, neutral project
  instructions, and root instruction files with the managed-block markers.

### Changed

- Role wrappers now also read the provider platform adapter, and every wrapper body is generated,
  so the four adapter surfaces stay consistent.
- `.claude/settings.json` and `.codex/hooks.json` are treated as shared project files: the installer
  adds its SessionStart hook once and never rewrites them.
- The in-project validator resolves the project root from its own location instead of the caller's
  working directory.
