# agent-kit

A development kit for building software with long-running Claude Code sessions. Drop it into a
repository and the agent gains one command per job — ship a feature, fix a bug, debug, review, set
up infrastructure — each backed by an ordered pipeline instead of improvised behavior.

The owner stays in the loop where judgement matters (what to build, and the technical design) and
steps out where it does not: after design approval the agent works through spec, plan,
implementation, tests, an independent code review, a security review, and a pull request without
asking routine questions.

```bash
# install into the current repository
curl -fsSL https://raw.githubusercontent.com/IliaSadovskii/agent-kit/main/install.sh | bash -s -- install

# later
.agent-kit/scripts/kit-update.sh
```

`.agent-kit/` holds canonical behavior; `.claude/` holds thin discovery wrappers pointing back at it.

## What you get

| Command | What it does |
|---|---|
| `/go` | Reads project state and routes you to the right workflow |
| `/ship [task]` | Front-loaded interaction, then autonomous through to a PR |
| `/fix [task]` | Lightweight path for a local, low-risk change |
| `/debug [symptom]` | Reproduce, isolate, root-cause, then fix with a regression test |
| `/review` | Independent read-only adversarial review of the current diff |
| `/test [target]` | Add or improve tests, then run the suite |
| `/docs` | Reconcile living documentation where it genuinely diverged |
| `/infra [local\|cloud]` | Interactive local or cloud provisioning |
| `/plan-next` | Read-only roadmap preview; builds nothing |
| `/riff [theme]` | Strategic brainstorm; builds nothing |

`ship --manual` swaps the autonomous contract for a consultative one with checkpoints, when you want
to co-develop rather than delegate.

## Install

Requirements: `bash`, `git`, and `sha256sum` (or `shasum`). `python3` is optional — it is only used
to merge the kit's hook into an existing `.claude/settings.json`.

```bash
cd your-project

# from the internet (installs the latest tagged release)
curl -fsSL https://raw.githubusercontent.com/IliaSadovskii/agent-kit/main/install.sh \
  | bash -s -- install

# or from a local clone, which is also how you test kit changes
git clone https://github.com/IliaSadovskii/agent-kit ~/src/agent-kit
bash ~/src/agent-kit/install.sh install --from ~/src/agent-kit
```

Useful flags: `--dry-run` (print, write nothing), `--ref v0.3.0` (pin a release),
`--dir path/to/project`.

Then:

1. **Review the diff and commit.** The kit is vendored into your repository on purpose — the agent
   reads plain files, and you can see in Git exactly what governs it.
2. **Start a fresh session.** Claude Code discovers commands, skills, and subagents at startup.
3. **Run `/go`.** On an unbootstrapped project it interviews you about the product, records where
   your docs live, generates only what is missing, and opens a bootstrap PR.

Installing into a repository that already has a `CLAUDE.md` is safe: the kit's imports go into a
marked block at the top and everything you wrote is kept below it.

See [docs/installing.md](docs/installing.md) for the full picture — what lands where, and what the
installer will and will not touch.

## Update

```bash
.agent-kit/scripts/kit-update.sh              # latest release
.agent-kit/scripts/kit-update.sh --dry-run    # preview
.agent-kit/scripts/kit-update.sh --ref v0.3.0 # pin
```

`.agent-kit/kit.lock` records, per file, what the release shipped and what your project had
afterwards. That is enough to tell three cases apart:

- **untouched** → replaced with the new version;
- **customized by you, unchanged upstream** → kept, silently;
- **changed on both sides** → kept, with the release copy parked next to it as `<file>.kit-new`,
  and listed at the end of the run.

Nothing under `.agent-kit/project/` is ever touched, and neither are your product docs, your code,
or anything outside the managed block in `CLAUDE.md`.

`install.sh status` shows the installed version, whether a newer release exists, and which kit files
you have edited locally. Details and the release-to-release notes are in
[docs/updating.md](docs/updating.md).

## Ownership boundary

| Kit-owned — replaced on update | User-owned — never touched |
|---|---|
| `.agent-kit/` except `project/` | `.agent-kit/project/manifest.yml`, `.agent-kit/project/instructions.md` |
| `.claude/commands/`, `.claude/skills/`, `.claude/agents/` | Your product docs, source, and tests |
| The `kit:managed` block in `CLAUDE.md` | The rest of `CLAUDE.md`, outside the managed markers |
| | `.claude/settings.json` (the kit only adds its hook once) |

Project-specific rules belong in `.agent-kit/project/instructions.md`, which no update rewrites. If
you find yourself editing a kit-owned file, that is a signal the change belongs upstream — send a
pull request instead of carrying a local fork.

## Architecture

```text
.agent-kit/               canonical behavior
  engine.md               governance: always-on baseline + workflow-scoped machinery
  workflows/              ordered pipelines — the single source of truth per workflow
  skills/                 detailed step behavior
  roles/                  tester / reviewer subagents
  rules/                  autonomous mode, interactive mode, pull requests
  project/                user-owned: manifest.yml + instructions.md
  scripts/                session setup, in-project validation, kit update
  kit.lock                what the installer put here, and at which version

.claude/                  discovery adapters only — every one points back at .agent-kit/
CLAUDE.md                 managed bootstrap block + your own overrides
```

The rule that keeps this maintainable: **behavior lives in exactly one canonical file, and adapters
never own behavior.** A wrapper that grows past a few lines is a bug — the repository's validator
enforces it.

## Developing the kit

```bash
scripts/validate.sh              # payload checks, a real install, and update semantics
scripts/generate-adapters.py     # regenerate every wrapper from catalog.tsv
```

Adding a workflow is one line in `catalog.tsv` plus the canonical file it points at. See
[docs/developing.md](docs/developing.md) for the release process.

## License

MIT — see [LICENSE](LICENSE). The `brainstorming` and `writing-plans` skills are adapted from
[Superpowers](https://github.com/obra/Superpowers) by Jesse Vincent; attribution and the original
license are in `kit/.agent-kit/NOTICE.md`.
