# Autonomous Agent Development Kit

A provider-neutral kit for building product features through long-running Claude Code or Codex
sessions. The owner participates in task selection, optional product ideation, and technical design;
after design approval the agent works autonomously until a pull request is ready.

This copy is installed in this project. The kit is developed and released separately — see
`.agent-kit/kit.lock` for the source repository and the installed version.

## Invocation

| Workflow | Claude Code | Codex | Behavior |
|---|---|---|---|
| Entry point | `/go` | `$go` | Reads project state and routes to the right workflow |
| Ship a feature | `/ship [task]` | `$ship [task]` | Front-loaded interaction, then autonomous to PR |
| Small change | `/fix [task]` | `$fix [task]` | Lightweight path for a local, low-risk change |
| Debug | `/debug [symptom]` | `$debug [symptom]` | Reproduce, isolate, root-cause, fix with a regression test |
| Review | `/review` | `$review` | Independent read-only adversarial review |
| Tests | `/test [target]` | `$test [target]` | Add or improve tests, then run the suite |
| Docs | `/docs` | `$docs` | Reconcile living documentation |
| Infrastructure | `/infra [local\|cloud]` | `$infra [local\|cloud]` | Interactive provisioning workflow |
| Preview next work | `/plan-next` | `$plan-next` | Read-only, builds nothing |
| Product riff | `/riff [theme]` | `$riff [theme]` | Interactive strategy, builds nothing |

Codex uses skills because repository custom prompts are not the portable workflow surface. A user
may also ask in natural language to "run ship", but explicit `$ship` is the deterministic form.

## Architecture and ownership

```text
.agent-kit/               canonical, provider-neutral behavior (kit-owned, replaceable)
  engine.md               always-on governance
  workflows/              ordered pipelines (single source of truth)
  skills/                 detailed step behavior
  roles/                  provider-neutral tester/reviewer roles
  rules/                  autonomous, interactive, and PR rules
  platforms/              capability mappings for each provider
  scripts/validate.sh     structural drift/broken-reference check
  scripts/kit-update.sh   update this kit from its source repository
  kit.lock                installed version, source ref, per-file checksums
  project/                user-owned, generated at bootstrap (never touched by an update)
    manifest.yml          automation state + doc paths
    instructions.md       shared project commands and conventions

.claude/                  Claude Code discovery adapter only
  commands/  skills/  agents/   thin wrappers pointing at .agent-kit/
  settings.json           shared project file; the kit only adds its SessionStart hook

.agents/skills/           Codex skill discovery wrappers
.codex/agents/            Codex custom-agent TOML wrappers
.codex/hooks.json         shared project file; the kit only adds its SessionStart hook
CLAUDE.md                 Claude bootstrap (managed block) + user provider overrides
AGENTS.md                 Codex bootstrap (managed block) + user provider overrides
```

An update replaces kit-owned files and rewrites only what sits between the
`<!-- kit:managed:start -->` / `<!-- kit:managed:end -->` markers in the root instruction files.
It never touches `.agent-kit/project/`, product docs, source code, or your override sections. A
kit-owned file you edited locally is preserved and reported as a conflict rather than overwritten.

## Updating

```bash
.agent-kit/scripts/kit-update.sh             # latest release
.agent-kit/scripts/kit-update.sh --dry-run   # preview
```

Project-specific rules belong in `.agent-kit/project/instructions.md`. Editing a kit-owned file
makes every future update to that file a manual merge — prefer upstreaming the change to the kit
repository recorded in `kit.lock`.

## The autonomous contract

The canonical sequence lives only in `.agent-kit/workflows/ship.md`. Before the design gate the
agent may ask one question at a time. After explicit design approval it must not pause for normal
ambiguity, recoverable tool failures, routine permission choices, or owner-only deployment work.
It chooses safe defaults, records assumptions/deviations and manual actions, runs independent
reviews, and continues to the PR. Only a genuinely insurmountable blocker may end the run early.

Cloud sessions should therefore be started with enough repository/provider permissions to create a
branch, run tests, push, and open a PR. Missing production secrets normally do not block feature
development; they become documented manual actions.

PR creation is capability-dependent. Claude Code and some Codex sessions expose GitHub actions to
the agent; Codex cloud also supports a post-task **Open PR** action in the product UI. When the
runtime has no agent-callable PR mechanism, Ship still finishes implementation and verification and
leaves the final diff/branch ready; opening the PR is then the only terminal manual action, never a
reason to interrupt implementation midway.

## Extending the kit

Changes belong in the kit repository, not in this installed copy:

- Add/reorder feature steps only in `.agent-kit/workflows/ship.md`.
- Put detailed reusable behavior in one canonical skill or role.
- Add only a thin discovery wrapper per provider — they are generated from the kit's catalog.
- Keep provider tool names and invocation syntax in `.agent-kit/platforms/` or wrappers.
- Add manifest keys instead of hardcoding user documentation paths.
- Run `.agent-kit/scripts/validate.sh` to check this project's copy for structural drift.

The adapted `brainstorming` and `writing-plans` material is attributed in `.agent-kit/NOTICE.md`.

## Provider references

- Claude Code: [project memory and imports](https://code.claude.com/docs/en/memory),
  [skills/commands](https://code.claude.com/docs/en/slash-commands),
  [subagents](https://code.claude.com/docs/en/sub-agents), and
  [hooks](https://code.claude.com/docs/en/hooks).
- Codex: [AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md),
  [skills](https://learn.chatgpt.com/docs/build-skills),
  [subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents),
  [hooks](https://learn.chatgpt.com/docs/hooks), and
  [cloud environments](https://learn.chatgpt.com/docs/environments/cloud-environment.md).
