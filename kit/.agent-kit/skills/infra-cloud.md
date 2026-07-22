# Infra — Cloud

> **LANGUAGE: talk to the user in the language from `.agent-kit/project/manifest.yml` → `language`.**
> These instructions are English; your messages to the user follow that value. Generated files,
> code, comments, and commit messages are English.

Take the project from "runs locally" to "reachable on the internet". This is the **Cloud** step
of the Infrastructure workflow. It runs **interactively** — hosting choice, credentials, and provisioning need the
owner's hands and judgment. The owner may **decline** it ("local only for now") — if so, record
that and stop cleanly; the fixed Infrastructure sequence allows skipping this phase.

<SCOPE>
Cloud deployment of the backend + the **release** mobile build (public backend URL). Local
containers/dev flow are `infra-local`. Shared Expo mechanics:
`.agent-kit/skills/references/mobile-env.md`. Hosting decision tree + provider trade-offs:
`.agent-kit/skills/infra-cloud/references/hosting-catalog.md`.
</SCOPE>

## What the agent does vs what the owner does

The agent CANNOT (and must not try to) provision real infrastructure autonomously — no buying a
VPS, no logging into a provider with the owner's credentials. The agent **generates config +
CI**, **guides step-by-step**, and **records every owner-hands action** in the runbook. The owner
executes the provider-console steps and supplies secrets. Never put a real secret in the repo
(engine rules 6–7) — config references env vars; real values live in the host's secret store.

## Idempotent

Read `manifest → infrastructure.cloud` first. `status: deployed` → show the current provider/URL
and offer to update (new CI, redeploy notes) rather than restart. `status: planned` → resume from
where it stopped.

## Checklist

Create a task per item and complete in order:

1. **Read state & prerequisites** — read `manifest.infrastructure.cloud` and confirm `infra-local`
   ran (a container image / compose is the usual deploy artifact). Note the backend stack.
2. **Survey what the owner has** — one question at a time, per the canonical hosting catalog's
   survey: existing VPS/cloud account/domain? budget posture? ops appetite? scale now? These pick
   the branch — don't present all providers at once.
3. **Recommend a path** — from the decision tree, propose ONE primary host + one fallback with the
   trade-offs (cost / managed-vs-hands-on / lock-in). Let the owner choose. Record the choice.
4. **Generate deploy artifacts** — for the chosen path, confirming each:
   - the platform config (e.g. `fly.toml`, a Render/Railway config, or the VPS `compose` +
     reverse-proxy for auto-TLS like Caddy/Traefik).
   - a **deploy CI pipeline** in whatever CI the repo uses (GitHub Actions / GitLab CI — detect
     it): build the image, push to a registry, deploy. Secrets referenced as CI variables, never
     inlined.
   - production env template: every var the deployed app needs, values as placeholders.
5. **Guide provisioning (owner-hands)** — walk the owner through the provider-console steps for the
   chosen path (create account/box, provision managed Postgres/Redis, set secrets in the
   dashboard/CI, point DNS, enable TLS). Each such step is logged to the runbook's manual-actions
   section (what / where / why / when).
6. **Capture the public backend URL** — once known, record it in
   `manifest.infrastructure.cloud.backend_url`. This is the handoff to the release mobile build.
7. **Release mobile build** (only if a mobile app was detected) — using the canonical mobile-env
   reference: set the EAS `production` profile's `EXPO_PUBLIC_API_URL` to the
   captured backend URL; document the store/distribution steps. Store submission (certs,
   provisioning profiles, store accounts, EAS credentials) is owner-hands → runbook manual actions.
8. **Write the runbook section** — create/update `docs/deployment.md` (path from
   `manifest.sources.deployment`) with a **"Cloud deployment"** section: the chosen host, the
   deploy command/CI flow, how to redeploy, the env vars and where they live, and a prominent
   **"Manual actions"** subsection (owner-only steps, mirroring the format in
   `.agent-kit/rules/pull-requests.md`).
9. **Update the manifest** — `infrastructure.cloud`: `status` (`planned` if the owner still has
   provisioning to do, `deployed` if it's live), `provider`, `backend_url`, and `configured_at`
   from the current session date.
10. **Commit** — generated CI/config + runbook + manifest on the current provider branch. Do not
    merge. Never commit a real secret.

## Security defaults (the Review step will check these)

- No real secrets in the repo or CI files — only references to CI/host secret stores.
- TLS on the public endpoint (PaaS-automatic, or Caddy/Traefik on a VPS).
- Least exposure: only the web port public; Postgres/Redis on the private network.
- `EXPO_PUBLIC_*` in the release build holds only non-secret config (it ships in the binary).

## What NOT to do (YAGNI)

- No autonomous provisioning via provider CLIs with the owner's credentials — guide, don't do.
- No Kubernetes / multi-region / autoscaling for an MVP — one clear host path.
- Don't invent infra the owner didn't agree to; prefer the simplest deploy that works.
