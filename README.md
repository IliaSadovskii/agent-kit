# agent-kit

A Claude Code plugin for autonomous feature development. Enable it and the agent gains a handful of
commands — ship a feature, fix what is wrong, run a sprint — each backed by an ordered pipeline
instead of improvised behavior.

The owner stays in the loop where judgement matters (what to build, and the technical design) and
steps out where it does not: after design approval the agent works through spec, plan,
implementation, tests, an independent code review, a security review, and a pull request without
asking routine questions.

## Install

```text
/plugin marketplace add IliaSadovskii/agent-kit
/plugin install agent-kit@agent-kit
```

That is the whole install. It also pulls in Anthropic's `code-review` and `pr-review-toolkit`
plugins, which the kit declares as dependencies — Claude Code resolves those automatically and lists
them at the end of the install. They supply review depth that Claude Code's bundled `/code-review`
has but cannot lend to an agent; see [the plugin's README](plugins/agent-kit/README.md#working-with-the-rest-of-claude-code)
for why. If they cannot be reached — a locked-down marketplace policy, a Claude Code old enough not
to ship the official marketplace — the kit still runs and reviews with its own agent instead.

Then start a fresh session and run `/agent-kit:ship`. On a project that has never used the kit it
interviews you about the product, records where your docs live, generates only what is missing, and
opens a bootstrap PR before it builds anything.

To pin the plugin for everyone working in a repository, commit it to the project's
`.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "agent-kit": { "source": { "source": "github", "repo": "IliaSadovskii/agent-kit" } }
  },
  "enabledPlugins": { "agent-kit@agent-kit": true }
}
```

Updates come from the plugin system: `/plugin update agent-kit@agent-kit`, or enable auto-update for
the marketplace.

## What you get

| Command | What it does |
|---|---|
| `/agent-kit:ship [task]` | Front-loaded interaction, then autonomous through to a PR |
| `/agent-kit:sprint [theme]` | One briefing sitting buys a queue of unattended ship runs — one mergeable PR at the end |
| `/agent-kit:fix [task] [--pr n]` | Something is wrong: your words, a PR review, or an observed failure |
| `/agent-kit:docs` | Reconcile living documentation where it genuinely diverged |
| `/agent-kit:screens` | Map every screen and transition, and keep the map true as the app grows |
| `/agent-kit:riff [theme]` | Strategic brainstorm; builds nothing — on a screen theme, the screens the app is missing |

`ship --manual` swaps the autonomous contract for a consultative one with checkpoints, when you want
to co-develop rather than delegate.

Six commands, and the list is meant to stay short. A command earns its place by being a pipeline you
could not get by asking in plain words — not by wrapping something Claude Code already does. Root-
cause debugging, a review round on an open PR, and proposing screens onto the map are all still
here; they are reached through `fix` and `riff` rather than through commands of their own.

## What it does not reinvent

The kit orchestrates; it delegates the parts Claude Code already does better. `ship` calls
`/code-review` for correctness on the finished diff, `/security-review` for the security pass,
`/verify` to confirm the change against the running app, and the built-in `Explore` and `Plan`
agents during design. Its own `reviewer` agent covers the one thing none of those can: whether the
diff matches the design that was approved for it.

## Ownership boundary

| The plugin's — replaced on update | The project's — never touched |
|---|---|
| Every file under `plugins/agent-kit/` | `.agent-kit/project/manifest.yml` and `instructions.md` |
| The skills, agents, rules, and hooks it installs | Your product docs, source, tests, and `CLAUDE.md` |

One file crosses that line on purpose — the screen map viewer, `docs/screens/screens.html`, which
`/agent-kit:screens` copies in and later replaces; see
[docs/developing.md](docs/developing.md#what-must-never-end-up-in-the-plugin). The map beside it is
yours.

Project-specific rules belong in `.agent-kit/project/instructions.md`, which no update rewrites. If
you find yourself wanting to edit a file inside the plugin, that is a signal the change belongs
upstream — send a pull request instead of carrying a local fork.

## Layout

```text
.claude-plugin/marketplace.json   this repository is also the marketplace
plugins/agent-kit/
  .claude-plugin/plugin.json      manifest
  engine.md                       always-on governance, injected at session start
  skills/                         one directory per command, plus the skills they call
  agents/                         reviewer and tester subagents
  rules/                          autonomous mode, interactive mode, pull requests
  templates/project/              what bootstrap copies into a project
  templates/screens/              the screen map viewer, copied by /agent-kit:screens
  hooks/, scripts/                session start, cloud dependency setup, and the guard that
                                  turns the never-rules into explicit confirmations
```

Behavior lives in exactly one file. A skill that only points at another file is a bug — the
repository's validator enforces it.

## Developing the kit

```bash
scripts/validate.sh    # manifest, frontmatter, structure, and reference checks
```

See [docs/developing.md](docs/developing.md) for the release process.

## License

MIT — see [LICENSE](LICENSE). The `brainstorming` and `writing-plans` skills are adapted from
[Superpowers](https://github.com/obra/Superpowers) by Jesse Vincent; attribution and the original
license are in `plugins/agent-kit/NOTICE.md`.
