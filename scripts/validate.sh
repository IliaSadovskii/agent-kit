#!/usr/bin/env bash
#
# Validate the plugin repository: manifests, skill and agent frontmatter, structure, and the
# references the skills make to files that ship alongside them.
# Run locally before a release; CI runs the same script.

set -uo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO" || exit 1

PLUGIN="plugins/agent-kit"

errors=0
fail() { printf 'ERROR: %s\n' "$1" >&2; errors=$((errors + 1)); }
step() { printf '\n== %s ==\n' "$1"; }

# --------------------------------------------------------------------------------------------
step "repository layout"

for path in VERSION CHANGELOG.md README.md .claude-plugin/marketplace.json \
            "$PLUGIN/.claude-plugin/plugin.json" "$PLUGIN/engine.md" "$PLUGIN/README.md" \
            "$PLUGIN/NOTICE.md" "$PLUGIN/hooks/hooks.json" \
            "$PLUGIN/templates/project/manifest.yml" \
            "$PLUGIN/templates/project/instructions.md"; do
  [ -e "$path" ] || fail "missing: $path"
done

VERSION="$(cat VERSION 2>/dev/null || echo)"
printf '%s' "$VERSION" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$' || fail "VERSION is not semver: $VERSION"
grep -q "## $VERSION" CHANGELOG.md 2>/dev/null || fail "CHANGELOG.md has no entry for $VERSION"

# A project's own corner must never ship inside the plugin — an update would overwrite it.
[ ! -e "$PLUGIN/.agent-kit" ] || fail "$PLUGIN/.agent-kit must not exist (project-owned)"

# The vendored-install machinery was removed in 0.4.0; it must not grow back.
for path in install.sh catalog.tsv kit templates scripts/generate-adapters.py; do
  [ ! -e "$path" ] || fail "pre-plugin artefact is back in the repository: $path"
done

grep -q '^bootstrapped: false' "$PLUGIN/templates/project/manifest.yml" \
  || fail "the manifest template must ship unbootstrapped"

# engine.md is delivered through a SessionStart hook, whose output Claude Code caps at 10,000
# characters. Past the cap it is written to a file and replaced with a preview, so the governance
# would silently stop being always-on.
engine_bytes="$(wc -c < "$PLUGIN/engine.md" 2>/dev/null || echo 0)"
[ "$engine_bytes" -lt 10000 ] \
  || fail "engine.md is $engine_bytes bytes; the SessionStart hook output cap is 10000"

# --------------------------------------------------------------------------------------------
step "manifests, frontmatter, and versions"

python3 - "$REPO" "$PLUGIN" "$VERSION" <<'PY'
import json, os, re, sys

repo, plugin, version = sys.argv[1], sys.argv[2], sys.argv[3]
errors = []

def load(path):
    try:
        with open(os.path.join(repo, path), encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as exc:                      # noqa: BLE001 - report, don't crash the run
        errors.append(f"{path}: {exc}")
        return None

market = load(".claude-plugin/marketplace.json")
manifest = load(f"{plugin}/.claude-plugin/plugin.json")

if market is not None:
    for field in ("name", "owner", "plugins"):
        if field not in market:
            errors.append(f"marketplace.json: missing required field {field!r}")
    entries = market.get("plugins") or []
    sources = [e.get("source") for e in entries]
    if f"./{plugin}" not in sources:
        errors.append(f"marketplace.json: no plugin entry with source ./{plugin}")

if manifest is not None:
    if manifest.get("name") != "agent-kit":
        errors.append("plugin.json: name must be 'agent-kit' (it namespaces every command)")
    if manifest.get("version") != version:
        errors.append(f"plugin.json version {manifest.get('version')!r} != VERSION {version!r}")

if market is not None and market.get("metadata", {}).get("version") not in (None, version):
    errors.append("marketplace.json metadata.version disagrees with VERSION")


def frontmatter(path):
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---\n", 3)
    if end == -1:
        return None, text
    block, body = text[4:end], text[end + 5:]
    fields = {}
    for line in block.splitlines():
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if m:
            fields[m.group(1)] = m.group(2).strip().strip('"')
    return fields, body


skills_dir = os.path.join(repo, plugin, "skills")
skill_names = set()
for name in sorted(os.listdir(skills_dir)):
    path = os.path.join(skills_dir, name, "SKILL.md")
    if not os.path.isfile(path):
        errors.append(f"skills/{name}: no SKILL.md")
        continue
    fields, body = frontmatter(path)
    if fields is None:
        errors.append(f"skills/{name}/SKILL.md: no YAML frontmatter")
        continue
    skill_names.add(name)
    if fields.get("name") != name:
        errors.append(f"skills/{name}/SKILL.md: frontmatter name {fields.get('name')!r} != directory name")
    desc = fields.get("description", "")
    if len(desc) < 40:
        errors.append(f"skills/{name}/SKILL.md: description is too thin to route on ({len(desc)} chars)")
    if len(desc) > 1024:
        errors.append(f"skills/{name}/SKILL.md: description is {len(desc)} chars; keep it well under the 1536 listing cap")
    # Behavior lives in exactly one file: a skill that only points somewhere else is the bug the
    # old adapter layer used to institutionalize.
    if len(body.strip()) < 400:
        errors.append(f"skills/{name}/SKILL.md: body is {len(body.strip())} chars — a pointer, not behavior")

agents_dir = os.path.join(repo, plugin, "agents")
for fname in sorted(os.listdir(agents_dir)):
    if not fname.endswith(".md"):
        continue
    fields, body = frontmatter(os.path.join(agents_dir, fname))
    stem = fname[:-3]
    if fields is None:
        errors.append(f"agents/{fname}: no YAML frontmatter")
        continue
    if fields.get("name") != stem:
        errors.append(f"agents/{fname}: frontmatter name {fields.get('name')!r} != file name")
    if len(fields.get("description", "")) < 40:
        errors.append(f"agents/{fname}: description is too thin to route on")

# Every command promised in the plugin README must exist as a skill, and vice versa.
readme = open(os.path.join(repo, plugin, "README.md"), encoding="utf-8").read()
documented = set(re.findall(r"/agent-kit:([a-z-]+)", readme))
for missing in sorted(documented - skill_names):
    errors.append(f"{plugin}/README.md documents /agent-kit:{missing}, which is not a skill")
for undocumented in sorted(skill_names - documented):
    # Skills the pipelines call internally do not need a README row.
    if undocumented in {"brainstorming", "writing-plans", "ideate", "idea-interview",
                        "docs-reflection"}:
        continue
    errors.append(f"skill {undocumented!r} is not documented in {plugin}/README.md")

for e in errors:
    print(f"ERROR: {e}", file=sys.stderr)
sys.exit(1 if errors else 0)
PY
[ $? -eq 0 ] || fail "manifest or frontmatter checks failed"

# --------------------------------------------------------------------------------------------
step "internal references resolve"

# Every ${CLAUDE_PLUGIN_ROOT}/... path a skill or agent mentions must exist in the payload.
while IFS= read -r ref; do
  target="$PLUGIN/${ref}"
  [ -e "$target" ] || fail "dangling reference: \${CLAUDE_PLUGIN_ROOT}/$ref"
done < <(grep -rhoE '\$\{CLAUDE_PLUGIN_ROOT\}/[A-Za-z0-9_./-]+' "$PLUGIN" \
           | sed 's|${CLAUDE_PLUGIN_ROOT}/||' | sed 's|[.,)]*$||' | sort -u)

# Paths from the pre-plugin layout must not survive anywhere in the payload.
stale="$(grep -rnE '\.agent-kit/(engine|skills|rules|workflows|roles|GUIDE|NOTICE|scripts|kit\.lock)' "$PLUGIN" || true)"
if [ -n "$stale" ]; then
  printf '%s\n' "$stale" >&2
  fail "payload references the pre-plugin .agent-kit/ layout"
fi

# --------------------------------------------------------------------------------------------
step "no project-specific leakage in the payload"

leaks="$(grep -rniE 'beeplish|english push tutor' "$PLUGIN" 2>/dev/null || true)"
if [ -n "$leaks" ]; then
  printf '%s\n' "$leaks" >&2
  fail "payload mentions a specific project"
fi

# --------------------------------------------------------------------------------------------
step "shell syntax"

while IFS= read -r script; do
  bash -n "$script" || fail "syntax error: $script"
  [ -x "$script" ] || fail "not executable: $script"
done < <(find . -name '*.sh' -not -path './.git/*')

if command -v shellcheck >/dev/null 2>&1; then
  shellcheck -S warning "$PLUGIN"/scripts/*.sh scripts/*.sh || fail "shellcheck reported problems"
else
  printf 'shellcheck not installed — skipped\n'
fi

# --------------------------------------------------------------------------------------------
step "claude plugin validate"

if command -v claude >/dev/null 2>&1; then
  claude plugin validate "./$PLUGIN" --strict || fail "claude plugin validate reported problems"
else
  printf 'claude CLI not available — skipped\n'
fi

# --------------------------------------------------------------------------------------------
printf '\n'
if [ "$errors" -ne 0 ]; then
  printf 'Validation failed with %s error(s).\n' "$errors" >&2
  exit 1
fi
printf 'Validation passed.\n'
