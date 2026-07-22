# Reference — cloud hosting decision tree (curated)

> Curated catalog used by `infra-cloud`. A **starting point, not gospel**: prices and free tiers
> drift, so treat the numbers as ballpark and confirm the current offer on the provider's site
> before recommending. The value here is the **decision tree** (which class of host fits which
> situation), not a live price sheet.

## First, survey what the owner already has

Before recommending anything, ask (one at a time, interactive):

1. **Existing resources?** Already-bought VPS, a cloud account (AWS/GCP/Hetzner/DO), a domain?
   → reuse it; skip the "which provider" branch.
2. **Budget posture?** "cheapest possible" / "cheap but managed" / "don't care, want easy".
3. **Ops appetite?** Willing to `ssh` into a box and run Docker, or wants push-to-deploy with
   zero server management?
4. **Scale now?** Hobby/MVP vs real traffic. Most early projects are hobby/MVP — don't
   over-provision.

The answers pick a branch below. Recommend ONE primary path + one fallback, not a menu of ten.

## The tree

### A. Owner already has a VPS / wants cheapest + hands-on
**Path: VPS + Docker Compose.** Provider e.g. Hetzner (cheapest reputable), or the box they own.
- Pros: cheapest (a few €/mo), full control, our generated `docker-compose.yml` runs almost as-is.
- Cons: owner manages the OS, updates, backups, TLS (use Caddy/Traefik for auto-HTTPS).
- Deploy: push image to a registry (or build on the box) + `docker compose up -d` via SSH in CI.
- Manual actions (→ runbook): buy/point the VPS, set DNS A-record, open firewall ports, put real
  secrets in the server's env / a `.env` on the box (never in the repo).

### B. Wants cheap-but-managed, push-to-deploy
**Path: a PaaS.** Fly.io, Railway, or Render.
- **Fly.io** — containers close to users, generous-ish free/low tier, `fly.toml` + `flyctl deploy`.
  Good when you want Docker but not a server.
- **Railway** — simplest DX, connect the repo and it builds; slightly pricier as you grow.
- **Render** — managed web service + managed Postgres/Redis add-ons, clean dashboard.
- Pros: no server to manage, managed Postgres/Redis available, TLS automatic.
- Cons: costs more than a bare VPS at scale; some lock-in to the platform's config format.
- Manual actions (→ runbook): create the account, connect the repo/registry, provision the
  managed DB/Redis add-on, set secrets in the platform's dashboard, point the custom domain.

### C. Wants "just make it easy", not cost-sensitive
**Path: Railway or Render**, managed everything (DB + Redis + web from one dashboard). Same as B
but bias to the simplest DX and don't optimize cost.

### D. Already committed to a big cloud (AWS/GCP/Azure)
**Path: their container service** (ECS/Fly-on-top, Cloud Run, Container Apps). Only go here if the
owner already lives there — otherwise it's more ops than an MVP needs. Cloud Run (GCP) is the
gentlest: deploy a container, scales to zero, pay per use.

## Backend URL is the handoff

Whatever path is chosen, the outcome that matters downstream is the **public backend URL**. Record
it in `manifest → infrastructure.cloud.backend_url`. The release mobile build (`infra-cloud`, via
`references/mobile-env.md`) bakes exactly this URL into the `production` profile.

## Non-negotiables regardless of path

- Real secrets NEVER in the repo — always the host's env/secret store; the runbook says where.
- TLS/HTTPS on the public endpoint (auto via the PaaS, or Caddy/Traefik on a VPS).
- Managed Postgres/Redis where offered beats self-hosting them for an MVP (backups included).
- Least exposure: only the web port is public; DB/Redis stay on the private network.
