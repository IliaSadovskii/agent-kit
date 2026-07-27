# Changelog

All notable changes to the kit. Versions follow semver from the perspective of a project that
installed it — see [docs/developing.md](docs/developing.md#versioning).

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
