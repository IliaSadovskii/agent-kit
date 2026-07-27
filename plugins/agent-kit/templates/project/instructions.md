# Project instructions (user-owned)

This file carries the project's own conventions for the agent kit. It belongs to the project: the
kit ships as a plugin and never writes here after bootstrap. Put Claude-only overrides in `CLAUDE.md`.

> **Boundary — keep this file mode-agnostic.** Put ONLY general project rules that hold in any mode
> (plain terminal work included): stack, commands, coding standards, branch policy. Anything specific
> to a workflow — the `ship` pipeline, design gates, the autonomous contract — belongs to the kit
> plugin, never here. This file is the always-on project baseline.

<!-- Bootstrap (idea-interview) fills the sections below for the detected stack. Until then they
     hold neutral defaults; replace the placeholders with this project's real commands. -->

## Cloud sessions

Hosted sandboxes split a network-enabled setup phase from a network-disabled agent phase, and do
not carry running services across that boundary. Respect the split:

- **Setup phase (network ON):** `scripts/cloud-setup.sh` installs everything reachable over the
  network — system packages and language dependencies. Claude Code runs it from the SessionStart
  hook. It must stay safe and idempotent when sourced locally.
- **Agent phase (network OFF):** never install dependencies here — it will fail with a proxy `403`.
  New dependencies must be added during the setup phase, or the environment must grant the agent
  internet access to the package registries. If a needed dependency cannot be installed, record it
  as a manual action instead of retrying.
- Before anything that touches real services (databases, migrations), start them with the project's
  service script; a suite that runs fully in-memory does not need it.
- Never commit real secrets; use the sandbox's test environment values.
- If a GitHub CLI is unavailable, use Claude Code's GitHub integration; commit and push with Git.
- Work on a feature branch, never directly on `main`.

## Commands

- Install dependencies: `<fill in>`
- Migrations: `<fill in>`
- Database: `<fill in>` (never substitute a different engine for production behavior)

## Verification

One line per layer this project can actually run. The agent takes these verbatim rather than
guessing, and adds a line here whenever it installs new test tooling — so the next session and CI
inherit it instead of rediscovering it.

- Full suite (what CI runs): `<fill in>`
- Type check: `<fill in>`
- Lint: `<fill in>`
- Unit tests: `<fill in>`
- Integration tests, and how to start what they need: `<fill in>`
- Contract tests between backend and frontend: `<none yet>`
- End-to-end: `<none yet>`
- Coverage report: `<none yet>`
- Mutation testing: `<none yet>`

Leave `<none yet>` where a layer is genuinely absent — that is the signal for the design step to
propose adding it, and it is more useful than a blank.

## Coding standards

Read the coding-standards document registered in `.agent-kit/project/manifest.yml` →
`sources.coding_standards` before implementing. In particular:

- KISS first; add patterns only for demonstrated duplication, coupling, or risk.
- Follow SOLID, pragmatic DRY, explicit behavior, and testable boundaries.
- `<add stack-specific conventions here>`
