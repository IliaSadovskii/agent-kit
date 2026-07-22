# Autonomous Agent Development Kit

A provider-neutral repository kit for building product features through long-running Claude Code
or Codex cloud sessions. Copy the kit into a project, bootstrap its product context once, then use
one command/skill per feature. The owner participates in task selection, optional product ideation,
and technical design; after design approval the agent works autonomously until a pull request is
ready.

## Invocation

| Workflow | Claude Code | Codex | Behavior |
|---|---|---|---|
| Ship a feature | `/ship [task]` | `$ship [task]` | Front-loaded interaction, then autonomous to PR |
| Preview next work | `/plan-next` | `$plan-next` | Read-only, builds nothing |
| Product riff | `/riff [theme]` | `$riff [theme]` | Interactive strategy, builds nothing |
| Infrastructure | `/infra [local\|cloud]` | `$infra [local\|cloud]` | Interactive provisioning workflow |

Codex uses skills because repository custom prompts are not the portable workflow surface. A user
may also ask in natural language to "run ship", but explicit `$ship` is the deterministic form.

## Architecture and ownership

```text
.agent-kit/               canonical, provider-neutral behavior (kit-owned, replaceable)
  engine.md               always-on governance
  workflows/              ordered pipelines (single source of truth)
  skills/                 detailed step behavior
  roles/                  provider-neutral tester/reviewer roles
  rules/                  autonomous and PR rules
  platforms/              capability mappings for each provider
  scripts/validate.sh     structural drift/broken-reference check
  project/                user-owned, generated at bootstrap (preserved on update)
    manifest.yml          automation state + doc paths
    instructions.md       shared project commands and conventions

.claude/                  Claude Code discovery adapter only
  commands/               /ship, /infra, /plan-next, /riff wrappers
  skills/                 canonical-skill wrappers
  agents/                 role wrappers
  settings.json           Claude lifecycle hook

.agents/skills/           Codex skill discovery wrappers
.codex/agents/            Codex custom-agent TOML wrappers
.codex/hooks.json         Codex lifecycle hook
CLAUDE.md                 Claude bootstrap + user provider overrides
AGENTS.md                 Codex bootstrap + user provider overrides
```

Kit-owned files may be replaced during a package update: an update replaces everything under
`.agent-kit/` **except** `.agent-kit/project/`. That subfolder (`manifest.yml` + `instructions.md`)
is user-owned and generated at bootstrap — preserve it, along with product docs, source code, and
user override sections in root instruction files.

## First run in a project

1. Copy `.agent-kit/`, `.claude/`, `.agents/`, `.codex/`, `CLAUDE.md`, and `AGENTS.md` into the
   repository root. Merge root instruction files when the project already has them; do not blindly
   overwrite existing instructions. Copy from a versioned release/archive, not an arbitrary working
   directory; never distribute personal files such as `.claude/settings.local.json`.
2. Ensure `scripts/cloud-setup.sh` exists and is safe/idempotent. The kit bootstrap can generate or
   adapt it for the detected stack.
3. Start Claude Code or Codex in the repository and invoke Ship.
4. If the manifest is absent/unbootstrapped, the agent interviews the owner, records existing docs
   by path, generates only missing foundations, fills shared project instructions, and opens a
   bootstrap PR. Merge it.
5. Invoke Ship again for the first feature.

Open a new task/session after installing or changing discovery adapters. Both providers discover
skills and subagents at session startup, although some clients can live-reload individual skills.

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

## Updating and extracting the kit

Until this directory has its own repository, treat `.agent-kit` plus the three discovery adapters
as one package. To extract it later:

1. Copy kit-owned files to the package repository.
2. Replace `.agent-kit/project/manifest.yml` and `.agent-kit/project/instructions.md` with clean templates.

Two markers make a future installer/updater (and safe manual merges) trivial today:

- **Managed sections** in `CLAUDE.md` / `AGENTS.md` are delimited by
  `<!-- kit:managed:start -->` … `<!-- kit:managed:end -->`. An update replaces only what is between
  the markers; the user override sections below them are preserved.
- **`kit_version`** in the manifest records the installed kit release, so an updater knows what to
  migrate.
3. Keep the adapter wrappers generated from one catalog of workflow/skill/role names.
4. Run `.agent-kit/scripts/validate.sh` in CI.
5. Version releases and provide an installer/updater that preserves user-owned files.

Do not use Codex's Claude import as the long-term update mechanism: it is useful for one-time
migration, but copied provider files are not a shared source of truth.

## Extending the kit

- Add/reorder feature steps only in `.agent-kit/workflows/ship.md`.
- Put detailed reusable behavior in one canonical skill or role.
- Add only a thin discovery wrapper per provider.
- Keep provider tool names and invocation syntax in `.agent-kit/platforms/` or wrappers.
- Add manifest keys instead of hardcoding user documentation paths.
- Validate that common files contain no `.claude/project.yml`, `.Codex`, provider branch prefix, or
  provider-only built-in command.

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
