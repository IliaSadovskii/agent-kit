# Project instructions (user-owned)

This file pins the reusable agent kit to this project. The kit never replaces it during an
update. Add shared project conventions here; put provider-only overrides in `CLAUDE.md` or
`AGENTS.md`.

> **Boundary — keep this file mode-agnostic.** Put ONLY general project rules that hold in any mode
> (plain terminal work included): stack, commands, coding standards, branch policy. Anything specific
> to a workflow — the `ship` pipeline, design gates, the autonomous contract — belongs in
> `.agent-kit/engine.md` or `.agent-kit/workflows/`, never here. This file is the "always-on"
> project baseline (see engine.md → "When these rules apply").

<!-- Bootstrap (idea-interview) fills the sections below for the detected stack. Until then they
     hold neutral defaults; replace the placeholders with this project's real commands. -->

## Cloud sessions

Hosted sandboxes split a network-enabled setup phase from a network-disabled agent phase, and do
not carry running services across that boundary. Respect the split:

- **Setup phase (network ON):** `scripts/cloud-setup.sh` installs everything reachable over the
  network — system packages and language dependencies. In Codex configure it as the environment
  "Setup script"; Claude Code runs it from the SessionStart hook. It must stay safe and idempotent
  when sourced locally.
- **Agent phase (network OFF):** never install dependencies here — it will fail with a proxy `403`.
  New dependencies must be added during the setup phase, or the environment must grant the agent
  internet access to the package registries. If a needed dependency cannot be installed, record it
  as a manual action instead of retrying.
- Before anything that touches real services (databases, migrations), start them with the project's
  service script; a suite that runs fully in-memory does not need it.
- Never commit real secrets; use the sandbox's test environment values.
- If a GitHub CLI is unavailable, use the provider's GitHub integration; commit and push with Git.
- Work on a feature branch, never directly on `main`.

## Commands

- Install dependencies: `<fill in>`
- Test suite: `<fill in>`
- Lint/static analysis: `<fill in>`
- Migrations: `<fill in>`
- Database: `<fill in>` (never substitute a different engine for production behavior)

## Coding standards

Read the coding-standards document registered in `.agent-kit/project/manifest.yml` →
`sources.coding_standards` before implementing. In particular:

- KISS first; add patterns only for demonstrated duplication, coupling, or risk.
- Follow SOLID, pragmatic DRY, explicit behavior, and testable boundaries.
- `<add stack-specific conventions here>`
