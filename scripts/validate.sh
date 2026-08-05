#!/usr/bin/env bash
#
# Validate the plugin repository: layout, manifests, versions, skill frontmatter, and the
# references the payload makes to files that ship alongside it.
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

for path in VERSION CHANGELOG.md README.md README.ru.md .claude-plugin/marketplace.json \
            "$PLUGIN/.claude-plugin/plugin.json" "$PLUGIN/README.md" \
            "$PLUGIN/templates/project.yml" "$PLUGIN/templates/knowledge"; do
  [ -e "$path" ] || fail "missing: $path"
done

VERSION="$(cat VERSION 2>/dev/null || echo)"
printf '%s' "$VERSION" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$' || fail "VERSION is not semver: $VERSION"
grep -q "## $VERSION" CHANGELOG.md 2>/dev/null || fail "CHANGELOG.md has no entry for $VERSION"

# A project's own corner must never ship inside the plugin — an update would overwrite it.
[ ! -e "$PLUGIN/.agent-kit" ] || fail "$PLUGIN/.agent-kit must not exist (project-owned)"

# The templates are read by blueprint instead of the format being restated in its prompt, so a
# template with no header comment is a file whose rules exist nowhere.
for tpl in "$PLUGIN"/templates/knowledge/*.md; do
  head -1 "$tpl" | grep -q '^<!--' \
    || fail "${tpl#"$REPO"/}: no header comment — the template is what defines the file's shape"
done

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
    if f"./{plugin}" not in [e.get("source") for e in market.get("plugins") or []]:
        errors.append(f"marketplace.json: no plugin entry with source ./{plugin}")

if manifest is not None:
    if manifest.get("name") != "agent-kit":
        errors.append("plugin.json: name must be 'agent-kit' (it namespaces every command)")
    if manifest.get("version") != version:
        errors.append(f"plugin.json version {manifest.get('version')!r} != VERSION {version!r}")

if market is not None and market.get("metadata", {}).get("version") not in (None, version):
    errors.append("marketplace.json metadata.version disagrees with VERSION")

# The storefront text went stale once (0.4.0 removed commands it kept advertising); keep it
# identical to plugin.json so it cannot drift again.
if market is not None and manifest is not None:
    for entry in market.get("plugins") or []:
        if entry.get("source") == f"./{plugin}" and entry.get("description") != manifest.get("description"):
            errors.append("marketplace.json plugin description != plugin.json description")

# A dependency on a plugin from another marketplace fails the install outright unless this
# marketplace — the root one, since it hosts what the user installs — allowlists that source.
if manifest is not None and market is not None:
    allowed = set(market.get("allowCrossMarketplaceDependenciesOn") or [])
    for dep in manifest.get("dependencies") or []:
        if isinstance(dep, dict) and dep.get("marketplace") and dep["marketplace"] not in allowed:
            errors.append(
                f"plugin.json depends on {dep.get('name')!r} from marketplace {dep['marketplace']!r}, "
                "which is not in marketplace.json allowCrossMarketplaceDependenciesOn"
            )


def frontmatter(path):
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---\n", 3)
    if end == -1:
        return None, text
    fields = {}
    for line in text[4:end].splitlines():
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if m:
            fields[m.group(1)] = m.group(2).strip().strip('"')
    return fields, text[end + 5:]


skills_dir = os.path.join(repo, plugin, "skills")
skill_names, stubs = set(), set()
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
        errors.append(f"skills/{name}/SKILL.md: description is {len(desc)} chars; keep it under the listing cap")
    # A command is either behavior or an declared stub. Anything in between is a command that looks
    # implemented and is not — which is worse than one that says so.
    if "Not written yet." in body:
        stubs.add(name)
    elif len(body.strip()) < 400:
        errors.append(f"skills/{name}/SKILL.md: body is {len(body.strip())} chars — neither behavior nor a declared stub")

# Every command promised in the plugin README must exist as a skill, and vice versa. A stub has to
# be marked as one there, so the README never advertises a command that does nothing.
readme = open(os.path.join(repo, plugin, "README.md"), encoding="utf-8").read()
documented = set(re.findall(r"/agent-kit:([a-z-]+)", readme))
for missing in sorted(documented - skill_names):
    errors.append(f"{plugin}/README.md documents /agent-kit:{missing}, which is not a skill")
for undocumented in sorted(skill_names - documented):
    errors.append(f"skill {undocumented!r} is not documented in {plugin}/README.md")
for name in sorted(stubs):
    if not re.search(rf"/agent-kit:{name}\b.*\bnot written\b", readme, re.I):
        errors.append(f"{plugin}/README.md must mark /agent-kit:{name} as not written yet")

for e in errors:
    print(f"ERROR: {e}", file=sys.stderr)
sys.exit(1 if errors else 0)
PY
[ $? -eq 0 ] || fail "manifest or frontmatter checks failed"

# The two READMEs are the kit's front door in two languages; one of them going stale is worse than
# not having it, and the command list is what a reader decides on.
en="$(grep -oE '/agent-kit:[a-z-]+' README.md | sort -u)"
ru="$(grep -oE '/agent-kit:[a-z-]+' README.ru.md | sort -u)"
[ "$en" = "$ru" ] || fail "README.md and README.ru.md document different commands"

# --------------------------------------------------------------------------------------------
step "internal references resolve"

# Every ${CLAUDE_PLUGIN_ROOT}/... path the payload mentions must exist in it.
while IFS= read -r ref; do
  [ -e "$PLUGIN/${ref}" ] || fail "dangling reference: \${CLAUDE_PLUGIN_ROOT}/$ref"
done < <(grep -rhoE '\$\{CLAUDE_PLUGIN_ROOT\}/[A-Za-z0-9_./-]+' "$PLUGIN" \
           | sed 's|${CLAUDE_PLUGIN_ROOT}/||' | sed 's|[.,)]*$||' | sort -u)

# --------------------------------------------------------------------------------------------
step "the payload's own markdown is not malformed"

# A single stray ``` turns everything after it into a code block. The file still looks fine in a
# diff, and the rules below the stray fence are read as a listing rather than as instructions —
# `blueprint` shipped like that for a release. Counting fences costs a millisecond.
while IFS= read -r md; do
  fences="$(grep -c '^```' "$md")"
  [ $((fences % 2)) -eq 0 ] || fail "${md#"$REPO"/}: $fences code fences — one of them is unclosed"
done < <(find "$PLUGIN" -name '*.md')

# HTML comments do not nest: an inner `-->` closes the outer block, and everything the author meant
# to hide from there on is rendered. The knowledge templates are all comment, so this is where it
# bites — and it shipped that way in screens.md.
python3 - "$PLUGIN" <<'PY'
import sys
from pathlib import Path

errors = []
for path in sorted(Path(sys.argv[1]).rglob("*.md")):
    depth, text = 0, path.read_text(encoding="utf-8", errors="replace")
    for index, token in enumerate(part for part in text.split("<!--")):
        if index and depth:
            errors.append(f"{path}: a comment opens inside another one — the first `-->` ends both")
            break
        depth = 1 if index else 0
        depth = 0 if "-->" in token else depth
    if depth:
        errors.append(f"{path}: a comment is never closed")

for e in errors:
    print(f"ERROR: {e}", file=sys.stderr)
sys.exit(1 if errors else 0)
PY
[ $? -eq 0 ] || fail "a markdown comment in the payload is malformed"

# --------------------------------------------------------------------------------------------
step "every field of the run file has a writer and a reader"

# Half the defects of the 5 August audit were records with only one side: a field a template
# declared and no instruction ever filled, or an instruction filling a field nothing read. Both are
# invisible in review and cost a whole release each.
#
# What this can prove is weaker than the rule: it counts the files that name a field, not what they
# do with it, so a generic name like `task` passes on prose alone. It still catches the case that
# actually happens — a field named in the template and nowhere else, or in one file only, which is
# a writer with no reader or the reverse.
python3 - "$REPO" "$PLUGIN" <<'PY'
import json, re, sys
from pathlib import Path

repo, plugin = Path(sys.argv[1]), sys.argv[2]
root = repo / plugin
template = root / "templates" / "run.json"
shape = json.loads(template.read_text(encoding="utf-8"))

payload = [p for p in sorted(root.rglob("*"))
           if p.is_file() and p.suffix in (".md", ".py", ".json", ".yml")
           and p != template and "__pycache__" not in p.parts]
texts = {p: p.read_text(encoding="utf-8", errors="replace") for p in payload}

errors = []
for field in [k for k in shape if not k.startswith("_")]:
    named = [p for p, text in texts.items() if re.search(rf"\b{re.escape(field)}\b", text)]
    if len(named) < 2:
        where = ", ".join(str(p.relative_to(root)) for p in named) or "nowhere"
        errors.append(f"run.json field {field!r} is named in {where} — a record with one side "
                      f"is written by nobody or read by nobody")

for e in errors:
    print(f"ERROR: {e}", file=sys.stderr)
sys.exit(1 if errors else 0)
PY
[ $? -eq 0 ] || fail "the run file declares a field the payload does not use"

# --------------------------------------------------------------------------------------------
step "no project-specific leakage in the payload"

leaks="$(grep -rniE 'beeplish|english push tutor' "$PLUGIN" 2>/dev/null || true)"
if [ -n "$leaks" ]; then
  printf '%s\n' "$leaks" >&2
  fail "payload mentions a specific project"
fi

# --------------------------------------------------------------------------------------------
step "the driver's own tests"

# orchestrate.py runs unattended overnight; the cheap place to find out it is wrong is here.
if [ -d tests ]; then
  python3 -m compileall -q "$PLUGIN/scripts" >/dev/null || fail "python syntax error under $PLUGIN/scripts"
  python3 -m unittest discover -s tests -q || fail "tests failed"
fi

# --------------------------------------------------------------------------------------------
step "shell syntax"

while IFS= read -r sh; do
  bash -n "$sh" || fail "syntax error: $sh"
  command -v shellcheck >/dev/null 2>&1 && { shellcheck -S warning "$sh" || fail "shellcheck: $sh"; }
done < <(find "$PLUGIN" scripts -name '*.sh' 2>/dev/null)

# --------------------------------------------------------------------------------------------
printf '\n'
if [ "$errors" -eq 0 ]; then
  printf 'OK — %s %s validates\n' "$PLUGIN" "$VERSION"
else
  printf '%d error(s)\n' "$errors" >&2
fi
exit $(( errors > 0 ))
