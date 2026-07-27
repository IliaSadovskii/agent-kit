# Pull request rules (flow rule)

The `PR` step opens the pull request following `.github/pull_request_template.md`, written in the
project language (`.agent-kit/project/manifest.yml` → `language`) — the section names below are
canonical, so translate them along with the body. Never merge; the owner merges.

Required sections:

- **What & why** — which roadmap task this closes.
- **Manual actions** — everything the owner must do by hand, consolidated from the whole feature
  (see `autonomous-mode.md`). For each: what, where, why, and when — before merge, before deploy,
  for device testing, or after merge. Typical entries: new secrets and where they go, access
  grants, third-party account setup, real-device build credentials, CI changes, production
  migrations. Say so explicitly when nothing is needed. Keep this near the top; the owner reads it
  first.
- **Architecture** — where the change plugs in and which layers it touches.
- **Changes** — the key files and their role.
- **Testing** — which tests, what they cover, and the run result.
- **Review** — the reviewer and security findings, and how each was closed.
- **Assumptions** — autonomous decisions taken, and any deviations from the approved design.
- A link to the cloud session when the session exposes one.
