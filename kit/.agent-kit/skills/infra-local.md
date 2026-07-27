# Infra — Local

Get a developer from a clean checkout to "the app runs on my machine" — backend in containers,
and, if the repo has a mobile app, a dev build that actually reaches the local backend. This is
the **Local** step of the Infrastructure workflow. It runs **interactively** (the owner is present):
propose, confirm, generate; do not silently invent a setup.

Local development only — cloud hosting, provisioning, and release builds are `infra-cloud`. The
mobile app is not a separate skill: this owns its dev variant, pointed at the local backend, while
the release variant belongs to `infra-cloud`. Shared Expo mechanics:
`.agent-kit/skills/references/mobile-env.md`.

## Stack-agnostic by detection

The logic ("containerize the backend", "wire the dev app URL") is universal; the stack-specific
part is detection + templates. Detect first, adapt, and **skip inapplicable branches**:

- Backend: `composer.json` → PHP/Laravel; `package.json` (server) → Node; `requirements.txt`/
  `pyproject.toml` → Python; `go.mod` → Go. Read the real services the project needs
  (Postgres/Redis/etc.) from config, don't assume.
- Mobile: `app.json` / `app.config.{ts,js}` + `expo` in `package.json`. Absent → skip the whole
  mobile branch (the project is backend-only).

Validated on Laravel+Expo, but write every step so a different detected stack slots in.

## Idempotent

Read `manifest → infrastructure.local` first. If `status: configured`, don't start from scratch:
show what exists, and offer to update/repair (regenerate a file, add a service) rather than
clobbering. Never overwrite a file the owner hand-edited without showing the diff and confirming.

## Checklist

Create a task per item and complete in order:

1. **Detect stack & read state** — backend language, needed services, mobile presence; read
   `manifest.infrastructure.local`. State in one line what you'll set up.
2. **Containerize the backend** — generate, confirming each:
   - `Dockerfile` — multi-stage, runs as a **non-root** user, minimal final image.
   - `docker-compose.yml` — the app + its real dependencies (e.g. Postgres, Redis) with named
     volumes; only necessary ports published; DB/Redis on the compose network, not the host where
     avoidable.
   - `.dockerignore` — excludes `.env`, `.git`, `node_modules`, `vendor`, build caches. It MUST
     keep `.env` and any secret out of the image.
   - `.env.example` — every var the app needs, with safe placeholder values; the real `.env` is
     git-ignored (verify `.gitignore` covers it).
3. **Build/run ergonomics** — a small `Makefile` (or `scripts/`) with `build` / `up` / `down` /
   `migrate` / `test` targets wrapping the compose commands, so the owner has one obvious way in.
   Follow whatever convention the repo already uses.
4. **Verify locally if possible** — if a container runtime is available in the session, build and
   boot once to confirm it comes up and migrations run; otherwise state that this is an owner
   verification step and put it in the runbook.
5. **Mobile dev build** (only if a mobile app was detected) — using
   `.agent-kit/skills/references/mobile-env.md`:
   - set `EXPO_PUBLIC_API_URL` for the **dev** variant to the local backend reachable from a
     phone — a **LAN IP** (same Wi-Fi) or a **tunnel** (`expo start --tunnel`/ngrok); explain to
     the owner why `localhost` won't work from the device.
   - wire the EAS `development` profile / dev-client if the project uses EAS; otherwise the plain
     `expo start` dev flow.
   - document the exact "start backend → set this URL → run on device/emulator" sequence.
6. **Write the runbook section** — create or update `docs/deployment.md` (path from
   `manifest.sources.deployment`) with a **"Local development"** section: prerequisites, the
   build/run commands, the mobile dev flow, and any owner-only step. Keep it a runnable checklist,
   not prose.
7. **Update the manifest** — set `infrastructure.local`: `status: configured`, `stack`,
   `artifacts` (the files generated), and `configured_at` from the current session date.
8. **Commit** — commit the generated infra files + runbook + manifest on the current provider
   branch. Do not merge. (Whether a PR is opened is decided by `infra`, not here.)

## What the Review step checks

Non-root container user; no secrets in the image or in `docker-compose.yml`, with env coming from a
git-ignored `.env`; a `.dockerignore` proven to exclude `.env` and `.git`; only the ports that must
be public published, databases on the internal network; and `EXPO_PUBLIC_*` holding non-secret
config only, since it ships inside the app bundle.

Docker Compose is the local target — production concerns (TLS, scaling, managed databases) belong
to `infra-cloud`.
