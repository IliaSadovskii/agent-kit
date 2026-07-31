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

# The screen map viewer is the one payload file that is copied into a project and then replaced by
# a later update. That exception to "once copied it belongs to that repository" is only safe while
# the file says so where whoever opens it will read it.
grep -q 'agent-kit:plugin-owned' "$PLUGIN/templates/screens/screens.html" \
  || fail "the screen map viewer must carry the agent-kit:plugin-owned marker in its header"

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
        if not isinstance(dep, dict):
            continue
        origin = dep.get("marketplace")
        if origin and origin not in allowed:
            errors.append(
                f"plugin.json depends on {dep.get('name')!r} from marketplace {origin!r}, which is "
                "not in marketplace.json allowCrossMarketplaceDependenciesOn — the install would fail"
            )


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
command_names = set()
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
    if fields.get("disable-model-invocation") == "true":
        command_names.add(name)
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
for undocumented in sorted(command_names - documented):
    errors.append(f"skill {undocumented!r} is not documented in {plugin}/README.md")

# Every /agent-kit:<name> reference in prose must name a live command. Dated records of what a
# release, a run, or a batch plans or did are not instructions anyone follows, so they are excluded.
excluded_dirs = (
    os.path.join(repo, "migrations"),
    os.path.join(repo, "docs", "specs"),
    os.path.join(repo, "docs", "plans"),
    os.path.join(repo, "docs", "design"),
    os.path.join(repo, ".agent-kit", "sprint"),
)
for dirpath, dirnames, filenames in os.walk(repo):
    dirnames[:] = [d for d in dirnames if d not in (".git", "node_modules")]
    if any(dirpath == d or dirpath.startswith(d + os.sep) for d in excluded_dirs):
        continue
    for fname in filenames:
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(dirpath, fname)
        if os.path.relpath(fpath, repo) == "CHANGELOG.md":
            continue
        text = open(fpath, encoding="utf-8").read()
        for name in re.findall(r"/agent-kit:([a-z-]+)", text):
            if name not in command_names:
                rel = os.path.relpath(fpath, repo)
                errors.append(f"{rel} references /agent-kit:{name}, which is not a live command")

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

# Skills take document paths only from the project manifest, so every `sources.<key>` the payload
# reads has to be a key the manifest template ships. Renaming one there is a silent break: the skill
# keeps naming a key nobody writes and reports the document as absent. `sources.screens` is read by
# three skills and written by one, which is exactly the spread that makes a rename look harmless.
while IFS= read -r key; do
  grep -qE "^  $key:" "$PLUGIN/templates/project/manifest.yml" \
    || fail "payload reads manifest sources.$key, which the manifest template does not ship"
done < <(grep -rhoE '\bsources\.[a-z_]+' "$PLUGIN" | sed 's|sources\.||' | sort -u)

# A template page and the scripts it loads are copied into a project together, so the same rule
# applies to them: a src the page names but the payload does not ship is a blank page in someone
# else's repository.
while IFS= read -r html; do
  while IFS= read -r src; do
    [ -e "${html%/*}/$src" ] || fail "$html loads a script that does not ship beside it: $src"
  done < <(grep -oE '<script[^>]*[[:space:]]src="[^"]*"' "$html" | sed 's/.*[[:space:]]src="//; s/"$//')
done < <(find "$PLUGIN/templates" -name '*.html')

# Paths from the pre-plugin layout must not survive anywhere in the payload.
stale="$(grep -rnE '\.agent-kit/(engine|skills|rules|workflows|roles|GUIDE|NOTICE|scripts|kit\.lock)' "$PLUGIN" || true)"
if [ -n "$stale" ]; then
  printf '%s\n' "$stale" >&2
  fail "payload references the pre-plugin .agent-kit/ layout"
fi

# --------------------------------------------------------------------------------------------
step "template payload syntax"

# A template page is loaded as a plain script from a file:// page, where a syntax error is a blank
# page and no message at all. Parse the payload's JavaScript here instead of in a browser.
if command -v node >/dev/null 2>&1; then
  while IFS= read -r js; do
    node --check "$js" || fail "syntax error: $js"
  done < <(find "$PLUGIN/templates" -name '*.js')

  # Every inline <script> of a template page, parsed but never run — vm.Script compiles, which is
  # exactly the check, and reading the page in node keeps the step to one interpreter.
  while IFS= read -r html; do
    node -e '
      const fs = require("fs"), vm = require("vm");
      const src = fs.readFileSync(process.argv[1], "utf8");
      const blocks = [...src.matchAll(/<script(?![^>]*\ssrc=)[^>]*>([\s\S]*?)<\/script>/g)];
      if (!blocks.length) process.exit(0);
      for (const [, code] of blocks) new vm.Script(code);
    ' "$html" || fail "syntax error in the inline script of: $html"
  done < <(find "$PLUGIN/templates" -name '*.html')

  # `node --check` parses but never runs. A data file that assigns the wrong global, or throws on
  # load, passes the parse and still reaches the owner as the same blank page — so load the screen
  # map's data the way the viewer does and check the viewer's own precondition. The error itself is
  # half the value of the check, so it is not swallowed.
  node -e '
    global.window = {};
    require(require("path").resolve(process.argv[1]));
    const d = global.window.SCREENS;
    if (!d || !Array.isArray(d.screens) || !d.screens.length) {
      throw new Error("no non-empty window.SCREENS after loading the file");
    }
  ' "$PLUGIN/templates/screens/screens.data.js" \
    || fail "the screen map demo data does not load into a non-empty window.SCREENS"

  # The demo map is what the format reference sends a reader to as the valid file, and a feature's
  # Docs step now edits a real map by the same two rules: allocate ids from the counters and raise
  # them, and give a card that reached `implemented` the `code` path that proves it. Neither rule is
  # visible in the viewer — a counter that has fallen behind hands out an id that is already taken,
  # which is the id reuse the format forbids — so an example that breaks one ships as the pattern.
  node -e '
    global.window = {};
    require(require("path").resolve(process.argv[1]));
    const d = global.window.SCREENS;
    const top = (items) => (items || []).reduce(
      (m, x) => Math.max(m, parseInt(String(x.id).slice(1), 10) || 0), 0);
    const bad = [];
    if (!(d.meta.nextScreenId > top(d.screens))) {
      bad.push(`meta.nextScreenId ${d.meta.nextScreenId} does not clear S${top(d.screens)}`);
    }
    if (!(d.meta.nextTransitionId > top(d.transitions))) {
      bad.push(`meta.nextTransitionId ${d.meta.nextTransitionId} does not clear T${top(d.transitions)}`);
    }
    for (const s of d.screens) {
      if (s.status === "implemented" && !s.code) bad.push(`${s.id} is implemented with no code path`);
    }
    if (bad.length) throw new Error(bad.join("; "));
  ' "$PLUGIN/templates/screens/screens.data.js" \
    || fail "the screen map demo data breaks a rule the skills tell a project's map to keep"
else
  printf 'node not available — skipped\n'
fi

# --------------------------------------------------------------------------------------------
step "no project-specific leakage in the payload"

leaks="$(grep -rniE 'beeplish|english push tutor' "$PLUGIN" 2>/dev/null || true)"
if [ -n "$leaks" ]; then
  printf '%s\n' "$leaks" >&2
  fail "payload mentions a specific project"
fi

# --------------------------------------------------------------------------------------------
step "python test suite and knowledge contract"

python3 -m unittest discover -s tests -t . || fail "python test suite failed"

# --skip-verification: this repository's own verification.commands names this very script, and
# without the flag the two would call each other forever.
python3 "$PLUGIN/scripts/knowledge_check.py" --skip-verification || fail "this repository's own knowledge contract failed --check"

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
