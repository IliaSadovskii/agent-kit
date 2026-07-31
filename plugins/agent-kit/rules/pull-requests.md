# Pull request rules (flow rule)

The `PR` step opens the pull request following `.github/pull_request_template.md`, written in the
project language (`.agent-kit/project/manifest.yml` → `language`) — the section names below are
canonical, so translate them along with the body. Never merge; the owner merges.

A pull request based on another feature's branch rather than the default branch — a stacked feature
inside a sprint — cannot land code at all: merging it moves the code into that branch. Give the body
a first line saying which sprint it belongs to, what it is based on, and that it reaches the default
branch through that sprint's integration pull request. Everything below is unchanged — this is still
where the feature is read and reviewed.

**Open it ready, convert it to a draft at the end of the run** (`gh pr ready --undo`). Draft is how
such a pull request is finally parked, not how it starts: the `code-review` plugin declines to
review a draft, so opening one as a draft silently costs the feature its strongest review. Convert
it yourself as the last thing the run does — including when the run ends on a blocker, because a
stacked pull request left ready is one merge click away from moving code sideways.

The description is written to be scanned. The owner decides in the first five lines whether this
is mergeable without reading the diff; everything below either helps that decision or collapses out
of the way. Structure beats prose: a Mermaid diagram when the change alters a flow (GitHub renders
it), tables for enumerable facts, `<details>` blocks for supporting evidence. A collapsed section's
`<summary>` line carries its conclusion — "Testing — 34 tests across 2 layers, all green" — so the
collapsed view still tells the whole story.

Sections, in order:

- **What & why** — five lines or fewer: what this closes, why it matters, and anything unusual
  about how. Which roadmap task it closes, when there is one.
- **Manual actions** — everything the owner must do by hand, consolidated from the plan's Run log
  across the whole feature. One line each: what, where, why, and when — before merge, before
  deploy, for device testing, or after merge. Typical entries: new secrets and where they go,
  access grants, third-party account setup, real-device build credentials, CI changes, production
  migrations. "None." explicitly when nothing is needed. Always visible, never collapsed — it is
  the section the owner acts on.
- **Assumptions** — autonomous decisions taken and any deviations from the approved design,
  assembled from the plan's Run log. A compact table — decision / why — and always visible: an
  assumption the owner never sees defeats the point of recording it. "None." when the run stayed
  inside the approved design.
- **Diagram** — when the change introduces or alters a flow, a Mermaid diagram of the new shape.
  Skip it for changes with no structure to draw.
- **Architecture** — where the change plugs in and which layers it touches. Collapsible.
- **Changes** — the key files and their role, as a table. Collapsible.
- **Testing** — which tests, what they cover, and the run result. Collapsible, with the verdict in
  the summary line.
- **Review** — the reviewer and security findings and how each was closed. Collapsible, findings
  count in the summary line. End it — outside the collapse — with the checks only the owner can
  start, as commands they can copy: `/code-review` on this branch for an independent multi-agent
  pass over correctness, and `/verify` to drive the running app. An agent cannot invoke either
  one, so this line is the only way they get offered — and the owner is reading this at exactly
  the moment a keystroke is cheap.
- A link to the cloud session when the session exposes one.
