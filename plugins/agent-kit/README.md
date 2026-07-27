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
infrastructure. `/code-review` and `/security-review` already do the first, plain conversation does
the second better than a command would, and the third was a separate product living inside this one.

## What is the plugin's, and what is the project's

```text
the plugin (replaced by every update)
  engine.md               always-on governance, injected by the SessionStart hook
  skills/                 one directory per command, plus the skills they call
  agents/                 reviewer and tester subagents
  rules/                  autonomous mode, interactive mode, pull requests
  templates/project/      what bootstrap copies into a project
  hooks/, scripts/        session start and cloud dependency setup

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

- **`/code-review`** for correctness on a finished diff — a multi-agent pass that scores its own
  findings for confidence and reports only what survives.
- **`/security-review`** for the security pass, with the `claude-security` plugin as the deeper
  option when a project has it enabled.
- **`/verify`** and **`/run`** to confirm a change against the running app rather than trusting a
  green test suite.
- The built-in **`Explore`** and **`Plan`** agents for codebase reconnaissance and competing
  architecture proposals during design.

The kit's own `reviewer` agent covers the one thing none of those can: whether the diff matches the
design that was approved for it.

Two kinds of plugin are worth having alongside the kit, though it requires neither:

- **A language server for your stack** — `typescript-lsp`, `pyright-lsp`, `gopls-lsp`, `ruby-lsp`,
  `php-lsp`, and the rest of the family in the official directory. The Build step is told to look
  for an existing helper before writing one, and find-references is how that search actually
  succeeds; without it the agent is guessing at names.
- **`pr-review-toolkit`** — Anthropic's specialist review agents, notably `silent-failure-hunter`
  and `pr-test-analyzer`. The kit covers both concerns itself, but a second opinion from a different
  author is worth more than a second opinion from the same one.

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
