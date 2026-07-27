# Autonomous Agent Development Kit

A kit for building product features through long-running Claude Code sessions. The owner
participates in task selection, optional product ideation, and technical design; after design
approval the agent works autonomously until a pull request is ready.

This copy is installed in this project. The kit is developed and released separately — see
`.agent-kit/kit.lock` for the source repository and the installed version.

## Invocation

| Command | Behavior |
|---|---|
| `/go` | Reads project state and routes to the right workflow |
| `/ship [task]` | Front-loaded interaction, then autonomous to PR |
| `/fix [task]` | Lightweight path for a local, low-risk change |
| `/debug [symptom]` | Reproduce, isolate, root-cause, fix with a regression test |
| `/review` | Independent read-only adversarial review |
| `/test [target]` | Add or improve tests, then run the suite |
| `/docs` | Reconcile living documentation |
| `/infra [local\|cloud]` | Interactive provisioning workflow |
| `/plan-next` | Read-only, builds nothing |
| `/riff [theme]` | Interactive strategy, builds nothing |

A user may also ask in natural language to "run ship", but the explicit `/ship` is the
deterministic form.

## Architecture and ownership

```text
.agent-kit/               canonical behavior (kit-owned, replaceable)
  engine.md               always-on governance
  workflows/              ordered pipelines (single source of truth)
  skills/                 detailed step behavior
  roles/                  tester / reviewer / plan-reviewer subagents
  rules/                  autonomous, interactive, and PR rules
  scripts/validate.sh     structural drift/broken-reference check
  scripts/kit-update.sh   update this kit from its source repository
  kit.lock                installed version, source ref, per-file checksums
  project/                user-owned, generated at bootstrap (never touched by an update)
    manifest.yml          automation state + doc paths
    instructions.md       shared project commands and conventions

.claude/                  Claude Code discovery adapters only
  commands/  skills/  agents/   thin wrappers pointing at .agent-kit/
  settings.json           shared project file; the kit only adds its SessionStart hook

CLAUDE.md                 kit bootstrap (managed block) + your own overrides
```

An update replaces kit-owned files and rewrites only what sits between the
`<!-- kit:managed:start -->` / `<!-- kit:managed:end -->` markers in `CLAUDE.md`. It never touches
`.agent-kit/project/`, product docs, source code, or your override section. A kit-owned file you
edited locally is preserved and reported as a conflict rather than overwritten.

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

Cloud sessions should therefore be started with enough repository permissions to create a branch,
run tests, push, and open a PR. Missing production secrets normally do not block feature
development; they become documented manual actions.

When the session has no agent-callable PR mechanism, Ship still finishes implementation and
verification and leaves the final diff/branch ready; opening the PR is then the only terminal
manual action, never a reason to interrupt implementation midway.

## Extending the kit

Changes belong in the kit repository, not in this installed copy:

- Add/reorder feature steps only in `.agent-kit/workflows/ship.md`.
- Put detailed reusable behavior in one canonical skill or role.
- Add only a thin discovery wrapper — they are generated from the kit's catalog.
- Add manifest keys instead of hardcoding user documentation paths.
- Run `.agent-kit/scripts/validate.sh` to check this project's copy for structural drift.

The adapted `brainstorming` and `writing-plans` material is attributed in `.agent-kit/NOTICE.md`.

## References

Claude Code: [project memory and imports](https://code.claude.com/docs/en/memory),
[skills and slash commands](https://code.claude.com/docs/en/slash-commands),
[subagents](https://code.claude.com/docs/en/sub-agents), and
[hooks](https://code.claude.com/docs/en/hooks).
