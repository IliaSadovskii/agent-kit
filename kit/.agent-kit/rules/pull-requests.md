# Pull Request rules (flow rule)

The `PR` step opens the pull request with a description following
`.github/pull_request_template.md`. Write it in the project language
(`.agent-kit/project/manifest.yml` → `language`).
Do NOT merge — the owner merges. Required sections:

- **What & why** — which roadmap task it closes.
- **Ручные действия** — everything the owner must do BY HAND that the agent cannot do itself,
  consolidated from the whole feature (see `autonomous-mode.md` → "Track manual actions"). For
  each: what, where, why, and when (before merge / before deploy / for device testing / after
  merge). Typical: new env vars / secrets and where to put them (`.env`, GitLab CI variables,
  hosting secrets), access grants, third-party accounts and their console setup, real-device build
  (certs/provisioning, EAS/store credentials), CI/CD or GitLab pipeline changes, manual prod
  migrations. If nothing is needed, say so explicitly. Near the TOP of the PR — the owner reads it
  first.
- **Architecture** — where it plugs in, which layers are touched.
- **Patterns** — which are applied and **why they are optimal** for this task.
- **Changes** — the key files and their role.
- **Testing** — which tests, what they cover, the run result.
- **Review** — which reviewer / security findings there were and how they were closed.
- **Assumptions / deviations** — autonomous decisions taken and any deviations from the approved
  design (see `autonomous-mode.md`).
- A link to the cloud session when the provider exposes one. Do not promise an automatic trailer.
