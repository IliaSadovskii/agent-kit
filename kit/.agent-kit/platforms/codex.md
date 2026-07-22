# Codex adapter

- Invocation: use the explicit skills `$ship`, `$infra`, `$plan-next`, and `$riff`. Natural-language
  requests such as "run ship" may implicitly select them when the client supports implicit skills.
- Skills are discovered under `.agents/skills/`; custom subagents under `.codex/agents/`; lifecycle
  hooks under `.codex/hooks.json`.
- Codex does not rely on Claude-style `@` imports in `AGENTS.md`. `AGENTS.md` therefore requires the
  agent to read `.agent-kit/engine.md`, `.agent-kit/project/instructions.md`, this file, and the manifest before
  acting.
- Prefer a branch prefix `codex/` unless the user or repository requires another prefix.
- Run code review and security review as two distinct passes. Use a dedicated available capability
  when present; otherwise spawn a fresh read-only reviewer for each pass.
- Use available GitHub tools to open a pull request; otherwise use authenticated `gh`. If neither is
  available, push the branch when possible and report PR creation as the final blocker, never as a
  mid-build question.
- Skill arguments are the text supplied with the invocation; treat them as workflow arguments.
- Codex cloud runs a network-enabled setup phase and a network-disabled agent phase, and keeps no
  running services or shell exports across that boundary. Configure the project's setup script
  (`scripts/cloud-setup.sh` convention) as the environment "Setup script"; it performs all
  network-bound dependency installation. If a hosted task starts without dependencies, run
  `AGENT_KIT_CLOUD=true scripts/cloud-setup.sh` before build/tests instead of asking the user.
- Never install dependencies during the agent phase — offline installs fail with a proxy `403`. A
  feature needing a new dependency must add it in the setup phase, or the environment must grant
  agent internet access to the relevant package registries. Otherwise record the install as a manual
  action, never a mid-build question.
- Before steps that require long-lived services (e.g. a database), run the project's documented
  hosted service bring-up; setup-phase services do not survive into the agent phase. Concrete
  commands and stack details live in `.agent-kit/project/instructions.md` → "Cloud sessions".
- Required Codex environment settings (owner configures once in the ChatGPT UI): env var
  `AGENT_KIT_CLOUD=true`; Setup script = the project's `scripts/cloud-setup.sh`; optionally an agent
  internet allowlist for the package registries the project's stack pulls from.
