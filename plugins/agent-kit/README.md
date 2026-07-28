# Agent Kit

A kit for building product features through long-running Claude Code sessions. The owner
participates in task selection, optional product scoping, and technical design; after design
approval the agent works autonomously until a pull request is ready.

## Commands

Plugin skills are namespaced, so every command below is `/agent-kit:<name>`.

| Command | Behavior |
|---|---|
| `/agent-kit:ship [task]` | Front-loaded interaction, then autonomous to PR |
| `/agent-kit:fix [task]` | Lightweight path for a local, low-risk change |
| `/agent-kit:debug [symptom]` | Reproduce, isolate, root-cause, fix with a regression test |
| `/agent-kit:address [pr]` | Close a review round on an open PR — comments and CI in, fixes and replies out |
| `/agent-kit:docs` | Reconcile living documentation |
| `/agent-kit:riff [theme]` | Interactive strategy, builds nothing |

The kit also ships two subagents, `agent-kit:reviewer` and `agent-kit:tester`, which the pipelines
invoke on finished work.

On a project that has never used the kit, run `/agent-kit:ship`: it detects the missing manifest and
runs the bootstrap interview before anything else.

Deliberately absent: there is no command for reviewing a diff, running tests, or provisioning
infrastructure. Claude Code's own `/code-review` and `/security-review` already do the first, plain
conversation does the second better than a command would, and the third was a separate product
living inside this one.

## What is the plugin's, and what is the project's

```text
the plugin (replaced by every update)
  engine.md               always-on governance, injected by the SessionStart hook
  skills/                 one directory per command, plus the skills they call
  agents/                 reviewer and tester subagents
  rules/                  autonomous mode, interactive mode, pull requests
  templates/project/      what bootstrap copies into a project
  hooks/, scripts/        session start, cloud dependency setup, and the guard hook

the project (never touched by an update)
  .agent-kit/project/manifest.yml     automation state and the paths to your documents
  .agent-kit/project/instructions.md  your stack, commands, and conventions
  CLAUDE.md, docs/, source, tests, secrets
```

The kit records where your documents live; it never moves or duplicates them. `bootstrapped: true`
in the manifest means the foundation exists, not that every future feature is specified.

To customize behavior, write to `.agent-kit/project/instructions.md`. Editing a file inside the
plugin means the next update overwrites it — send the change upstream instead.

## Working with the rest of Claude Code

The kit does not reimplement what Claude Code already does well. The pipelines call:

- **`/security-review`** for the security pass, with the `claude-security` plugin as the deeper
  option when a project has it enabled.
- **`/simplify`** to keep a large diff readable, and **`/run`** to drive the app while debugging.
- The built-in **`Explore`** and **`Plan`** agents for codebase reconnaissance and competing
  architecture proposals during design.

**What an agent cannot call.** The bundled `/code-review` and `/verify` are marked
`disable-model-invocation`: only a person typing them starts them, in any session. That is a property
of those skills, not a setting you can change, so the kit never pretends to run them. Instead the
`reviewer` agent covers correctness and design conformance itself, the Test step drives the app with
the project's own commands, and both bundled checks are offered in the PR description as
one-keystroke second opinions at the moment the owner is already reading.

Two Anthropic plugins close most of that gap, because plugin commands and agents *are*
model-invocable. The kit uses them when a project has them enabled and works without them:

```text
/plugin install pr-review-toolkit@claude-plugins-official
/plugin install code-review@claude-plugins-official
```

The official marketplace ships pre-configured with Claude Code, so there is no marketplace to add.
`pr-review-toolkit` supplies specialist review agents the kit delegates to during Review;
`code-review` supplies a multi-agent, confidence-scored pass that the PR step runs on the open pull
request. Install them once at user scope and every project has them, or declare them in a project's
`.claude/settings.json` to pin them for everyone working in that repository.

Two kinds of plugin are worth having alongside the kit, though it requires neither:

- **A language server for your stack** — `typescript-lsp`, `pyright-lsp`, `php-lsp`, `go-lsp`,
  `rust-lsp`, and the rest of the family in the official directory. The Build step is told to look
  for an existing helper before writing one, and find-references is how that search actually
  succeeds; without it the agent is guessing at names.
- **`pr-review-toolkit`** and **`code-review`** — see "What an agent cannot call" above. These are
  the plugins that give back the review depth the bundled `/code-review` has and cannot lend to an
  agent, and they are the highest-value pair to enable alongside this kit.

Writing tests is deliberately not delegated. Everything the kit hands off inspects finished work,
which is why a generic version of it can exist at all; authoring tests means writing code inside
this project's conventions, framework, and seams, and there is no generic version of that.

## The autonomous contract

The canonical sequence lives in the `ship` skill. Before the design gate the agent may ask one
question at a time. After explicit design approval it must not pause for normal ambiguity,
recoverable tool failures, routine permission choices, or owner-only deployment work. It chooses
safe defaults, records assumptions and manual actions, runs the independent reviews, and continues
to the PR. Only a genuinely insurmountable blocker may end the run early.

Start long runs in [auto mode](https://code.claude.com/docs/en/permission-modes)
(`claude --permission-mode auto`, or Shift+Tab until the status bar shows it) so routine permission
prompts do not stall an unattended session. Cloud sessions need enough repository permission to
create a branch, run tests, push, and open a PR. Missing production secrets normally do not block
feature development; they become documented manual actions.

When the session has no agent-callable PR mechanism, `ship` still finishes implementation and
verification and leaves the branch ready; opening the PR is then the only terminal manual action,
never a reason to interrupt implementation midway.

Attribution for adapted material is in [NOTICE.md](NOTICE.md).
