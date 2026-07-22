# Reference — mobile env-per-variant (Expo/RN)

> Shared reference pulled in by BOTH `infra-local` (dev build) and `infra-cloud` (release
> build). The mobile app is not a separate skill — it is an **environment axis** that both
> skills handle for their own side. This file describes the one thing that differs between a
> dev build and a release build: **which backend URL (and env) is baked into the app**. Every
> other piece of the mobile toolchain is identical across variants, so it lives here once (DRY).

Applies only when the repo actually contains an Expo/RN app — detect it before using this
(`app.json` / `app.config.{ts,js}` present, and `expo` in `package.json` dependencies). No
mobile app → skip everything here.

## The core problem (for a backend-minded reader)

A phone does **not** see the dev machine's `localhost` — `localhost` on the phone is the phone
itself, not your laptop running the backend. So the API base URL baked into the app must be:

- **dev build** → the dev machine reachable from the phone: a **LAN IP** (`http://192.168.x.y:8000`)
  when both are on the same Wi-Fi, or a **tunnel** (`expo start --tunnel`, or ngrok) otherwise.
  This is `infra-local`'s job.
- **release build** → the public backend URL (`https://api.example.com`) that only exists after
  the cloud backend is deployed. This is `infra-cloud`'s job, and it depends on the cloud
  backend URL (`manifest → infrastructure.cloud.backend_url`).

Same toolchain, different value. That single value is the whole story.

## How the value gets in

- **`EXPO_PUBLIC_*` env vars** — anything prefixed `EXPO_PUBLIC_` is inlined into the JS bundle
  at build time and readable as `process.env.EXPO_PUBLIC_API_URL`. Simplest path; use this for
  the API base URL.
- **`app.config.ts` → `extra`** — for values you want computed per profile; read at runtime via
  `expo-constants` (`Constants.expoConfig.extra.apiUrl`). Use when the value is more than a plain
  string or must vary by build profile programmatically.

Prefer `EXPO_PUBLIC_API_URL` for the URL; reach for `extra` only when there is a real reason.

## EAS build profiles & channels

`eas.json` defines build **profiles** — conventionally `development`, `preview`, `production`.
Each profile carries its own env (its own `EXPO_PUBLIC_API_URL`), so one command per variant
produces a binary pointed at the right backend:

- `development` → dev client, points at the local/tunnel backend (paired with `infra-local`).
- `preview` → internal-distribution build against a staging backend (optional).
- `production` → store build against the public backend (paired with `infra-cloud`).

OTA-update **channels** map to profiles so `eas update` ships JS to the matching audience. Only
introduce channels if the project uses EAS Update; otherwise a plain per-profile build is enough
(YAGNI).

## What each skill owns

- `infra-local` — the `development` profile + the LAN-IP/tunnel decision + a documented
  "run backend → set this URL → launch on device/emulator" flow.
- `infra-cloud` — the `production` profile pointed at `infrastructure.cloud.backend_url` + the
  store/distribution steps (which are owner-hands: certs, provisioning, store accounts → these go
  to the runbook's manual-actions section).

Never bake secrets into the app bundle — `EXPO_PUBLIC_*` is **public** (shipped in the binary).
Only non-secret config (URLs, public keys) goes there; real secrets stay server-side.
