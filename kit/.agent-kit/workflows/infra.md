# Infrastructure workflow

`infra` stands the project up locally and optionally in the cloud. It is project-level and
interactive because hosting choices, credentials, domains, and provisioning require owner input.
It deliberately does not use the feature spec/plan/tester pipeline.

Arguments: `local` runs only Local, `cloud` runs only Cloud. These explicit arguments run their
stage directly, unchanged.

When invoked interactively without an explicit stage argument (via `/go`, or with no argument),
present a sub-menu and let the owner choose rather than silently running Local → Cloud:

| Choice | Action |
|---|---|
| `local` | Run the Local stage (below). |
| `cloud` | Run the Cloud stage (below). The owner may decline. |
| `status` | Read `manifest.infrastructure` and report the current local/cloud state without changing anything — no detection, no writes. |
| `update` | Re-detect the real stack and services and repair/refresh the configured state idempotently, rather than provisioning from scratch. |

## Pipeline — single source of truth

- **Detect** — read `.agent-kit/project/manifest.yml`, project files, and existing infrastructure state.
  Detect the real stack and services; update/repair configured state instead of regenerating it.
- **Local** — unless only `cloud` was requested, run `infra-local`: containerize the backend,
  provide build/run commands, wire any dev mobile build to the reachable local backend, verify when
  possible, update the deployment runbook, and update manifest state.
- **Cloud** — unless only `local` was requested, run `infra-cloud`: survey existing resources and
  constraints one question at a time, recommend one primary host and fallback, generate deployment
  config/CI, guide owner-only provisioning, capture the public backend URL, wire release mobile
  configuration, and update runbook/manifest state. The owner may decline.
- **Review** — perform a separate security/sanity review of the infrastructure diff: non-root
  containers, no secrets committed or baked, safe `.dockerignore`, minimal port exposure, private
  databases, TLS for public endpoints, and no secrets in public mobile variables. Fix findings.
- **Runbook and state** — verify the deployment source registered in the manifest is runnable and
  that `manifest.infrastructure` matches the generated artifacts and real provisioning state.
- **Delivery** — use the active provider's branch convention, commit coherent changes, push/open a
  PR in a hosted session when possible, and never merge.
