# agent-kit

A Claude Code plugin for building software with long-running sessions. It is being rebuilt.

Version 1 starts from an empty command set and adds one command at a time, each on its own
argument, after a measured run of 0.17.0 showed that most of the kit's machinery existed to insure
it against its own autonomy — and that the insurance had started to confuse the agents reading it.
The diagnosis, the decisions, and what is deliberately still open are in
[docs/design/kit-v1.md](docs/design/kit-v1.md).

**Today only `/agent-kit:blueprint` works.** The other four commands are declared so the shape is
visible, and do nothing when invoked. If you want the last complete version, install the `v0.17.0`
tag instead.

## Install

```text
/plugin marketplace add IliaSadovskii/agent-kit
/plugin install agent-kit@agent-kit
```

To pin it for everyone working in a repository, commit it to the project's `.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "agent-kit": { "source": { "source": "github", "repo": "IliaSadovskii/agent-kit" } }
  },
  "enabledPlugins": { "agent-kit@agent-kit": true }
}
```

Updates come from the plugin system: `/plugin update agent-kit@agent-kit`.

## The commands

| Command | What it does |
|---|---|
| `/agent-kit:blueprint` | the project's knowledge layer: the interview, and `--check` that audits it |
| `/agent-kit:fix` | something is wrong and it is small — not written yet |
| `/agent-kit:ship` | one feature, end to end — not written yet |
| `/agent-kit:sprint` | a batch of features, autonomous — not written yet |
| `/agent-kit:mvp` | from the blueprint to a running prototype — not written yet |

Blueprint is what the other four stand on: run it first, and it interviews you into
`docs/knowledge/` — what the product is and deliberately is not, the stack and the rules the build
follows, the actors, entities, actions, screens, integrations, the scenarios that must pass, and
the MVP bounds. See [the plugin's README](plugins/agent-kit/README.md) for how it is written and
kept true.

## Working on the kit itself

`scripts/validate.sh` checks the layout, the manifests, version agreement, skill frontmatter and
internal references; CI runs the same script. Release notes live in
[CHANGELOG.md](CHANGELOG.md), the process in [docs/developing.md](docs/developing.md).

MIT licensed.
