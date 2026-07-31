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
            "$PLUGIN/NOTICE.md" "$PLUGIN/hooks/hooks.json" "$PLUGIN/pipelines.default.yml" \
            "$PLUGIN/templates/project/manifest.yml" \
            "$PLUGIN/templates/project/instructions.md" \
            "$PLUGIN/templates/project/contract.yml"; do
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
# would silently stop being always-on. The same hook now prints the branch's unfinished run state
# after it, so engine.md's budget is the cap minus whatever the gate is allowed to add.
state_cap="$(python3 -c 'import re,sys
print(re.search(r"^STATE_CAP = (\d+)", open(sys.argv[1], encoding="utf-8").read(), re.M).group(1))' \
  "$PLUGIN/scripts/kit_gate.py" 2>/dev/null || echo 0)"
[ "$state_cap" -gt 0 ] || fail "kit_gate.py declares no STATE_CAP for the gate's share of the hook"
engine_bytes="$(wc -c < "$PLUGIN/engine.md" 2>/dev/null || echo 0)"
[ "$((engine_bytes + state_cap))" -lt 10000 ] \
  || fail "engine.md is $engine_bytes bytes and the gate may add $state_cap; the SessionStart hook \
output cap is 10000"

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
commands = set()          # the skills a user can type: disable-model-invocation marks them
skill_fields = {}
skill_bodies = {}
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
    skill_fields[name] = fields
    skill_bodies[name] = body
    if fields.get("disable-model-invocation") == "true":
        commands.add(name)
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
                        "docs-reflection", "stack-playbook", "debug", "address", "screens-riff"}:
        continue
    errors.append(f"skill {undocumented!r} is not documented in {plugin}/README.md")

# Absorbing a command into another one leaves nothing broken behind: the skill still works when a
# pipeline invokes it by name, so a `/agent-kit:<gone>` left in the payload fails silently — the
# reader types a command that is not in their list. Every command reference the payload or the
# storefront makes must therefore name a skill that still carries `disable-model-invocation`.
# History is exempt and lives elsewhere: CHANGELOG.md and migrations/ name removed commands on
# purpose, and so do the design documents under docs/.
sources = [os.path.join(repo, "README.md")]
for root, dirs, files in os.walk(os.path.join(repo, plugin)):
    sources.extend(os.path.join(root, f) for f in sorted(files))
for path in sorted(sources):
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except (OSError, UnicodeDecodeError):
        continue
    for name in sorted(set(re.findall(r"/agent-kit:([a-z-]+)", text)) - commands):
        where = os.path.relpath(path, repo)
        if name in skill_names:
            errors.append(f"{where} writes /agent-kit:{name}, but {name!r} is an internal skill, "
                          "not a command anyone can type")
        else:
            errors.append(f"{where} writes /agent-kit:{name}, which is not a skill at all")

# The storefront README is the other half of that promise: the plugin README is cross-checked
# against the skill list in both directions above, the root one not at all. A command whose row
# leaves one table and stays in the other is invisible to a reader of the wrong file, and the two
# tables are edited by hand, one commit apart.
root_readme = open(os.path.join(repo, "README.md"), encoding="utf-8").read()
root_documented = set(re.findall(r"/agent-kit:([a-z-]+)", root_readme))
for missing in sorted(commands - root_documented):
    errors.append(f"README.md does not document /agent-kit:{missing}, which is a command "
                  "(the plugin README and the storefront must list the same set)")

# The storefront counts the commands in prose, and the count is the first thing to go stale when
# one is absorbed into another — 0.17.0 had to rewrite "Nine commands" by hand. Only a sentence
# that states a number is checked, so rewording the claim away is free.
NUMBERS = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve".split())}
for token in re.findall(r"\b([A-Za-z]+|\d+) commands\b", root_readme):
    stated = int(token) if token.isdigit() else NUMBERS.get(token.lower())
    if stated is not None and stated != len(commands):
        errors.append(f"README.md says {token!r} commands; {len(commands)} skills carry "
                      "disable-model-invocation: true")

# `argument-hint` is read only when the skill is typed as a slash command. Left on a skill that a
# pipeline now invokes, it is the visible half of a command that is no longer in anyone's list —
# the leftover that makes "absorbed" look half-done to the next reader of the frontmatter.
for name in sorted(skill_names - commands):
    if "argument-hint" in skill_fields[name]:
        errors.append(f"skills/{name}/SKILL.md carries argument-hint but not "
                      "disable-model-invocation: true — argument-hint is read for a slash command "
                      "only, so it advertises arguments to a menu row that does not exist")

# The mirror image: a command that reads `$ARGUMENTS` takes arguments by definition, and without a
# hint the command list offers no clue what to type after it.
for name in sorted(commands):
    if "$ARGUMENTS" in skill_bodies[name] and "argument-hint" not in skill_fields[name]:
        errors.append(f"skills/{name}/SKILL.md is a command whose body reads $ARGUMENTS but "
                      "declares no argument-hint")

# An internal skill is reached one way only: another skill names it. Its description says which one
# — that is the shape every internal skill in the payload uses, and for a skill absorbed out of the
# command list it is the only remaining record of who calls it. Both halves have to be true, so
# check the caller back: if the routing paragraph that replaced the command is ever rewritten away,
# the skill keeps working when invoked and nothing invokes it, which no other check here would see.
def names(needle, text):
    return re.search(rf"(?<![\w-]){re.escape(needle)}(?![\w-])", text) is not None

for name in sorted(skill_names - commands):
    desc = skill_fields[name].get("description", "")
    parts = re.split(r"invoked", desc, maxsplit=1, flags=re.I)
    callers = ([s for s in sorted(skill_names) if s != name and names(s, parts[1])]
               if len(parts) == 2 else [])
    if not callers:
        errors.append(f"skills/{name}/SKILL.md is internal, and its description does not say it is "
                      "invoked by a named skill — for a skill nobody can type, that clause is the "
                      "routing signal and the only record of who calls it")
        continue
    # The caller must actually route to it. A skill is named as `name` in the payload's prose, and
    # only that form is a reference rather than the English word: `address` is what fix runs,
    # "address" is what a review comment does.
    if not any(f"`{name}`" in skill_bodies[c] for c in callers):
        errors.append(f"skills/{name}/SKILL.md says it is invoked by {', '.join(callers)}, but no "
                      f"body there names `{name}` — nothing reaches this skill any more")

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
step "payload scripts import the standard library only"

# A hook or a check that dies on ImportError on someone else's machine takes the whole kit with it,
# and the kit installs no dependencies. Parsing beats grepping: an import inside a function or a
# try/except is still an import at run time.
python3 - "$REPO/$PLUGIN" <<'PY'
import ast, os, sys

root = sys.argv[1]
errors = []
for base, _, files in os.walk(root):
    siblings = {f[:-3] for f in files if f.endswith(".py")}
    for name in sorted(f for f in files if f.endswith(".py")):
        path = os.path.join(base, name)
        with open(path, encoding="utf-8") as fh:
            try:
                tree = ast.parse(fh.read(), filename=path)
            except SyntaxError as exc:
                errors.append(f"{path}: {exc}")
                continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                modules = [] if node.level else [(node.module or "").split(".")[0]]
            else:
                continue
            for module in modules:
                if module and module not in sys.stdlib_module_names and module not in siblings:
                    errors.append(f"{os.path.relpath(path, os.path.dirname(root))}: line "
                                  f"{node.lineno} imports {module!r}, which is neither the standard "
                                  "library nor a module shipped beside it")
for e in errors:
    print(f"ERROR: {e}", file=sys.stderr)
sys.exit(1 if errors else 0)
PY
[ $? -eq 0 ] || fail "the payload imports something it does not ship"

# --------------------------------------------------------------------------------------------
step "python tests"

# The repository's own test layer: plain executable checks over the scripts the payload ships.
# A loop over a glob is silent when the glob is empty, and a test step that finds no tests is the
# one failure mode nothing downstream would notice — so count them first.
mapfile -t tests < <(find tests -name 'test_*.py' 2>/dev/null | sort)
if [ "${#tests[@]}" -eq 0 ]; then
  fail "no tests found under tests/ — the suite cannot pass by being absent"
fi
for test in "${tests[@]}"; do
  python3 "$test" || fail "tests failed: $test"
done

# --------------------------------------------------------------------------------------------
step "mutation testing over the step gate"

# The gate is the one script here whose tests passing while the code is wrong would be invisible:
# nothing downstream re-checks a step's verdict, so a gate that passes a step it should have failed
# reports success in the voice of success. `tests/mutate_gate.py` breaks kit_gate.py 117 ways and
# requires tests/test_gate.py to notice each one.
#
# It costs one suite run per mutant — around a quarter of an hour, against fifteen seconds for
# everything else in this file. Run unconditionally it would turn the pre-release check into
# something people skip, and a check people skip is worse than one that says it did not run. So it
# is on in CI, where the wall clock is nobody's afternoon, and off locally unless asked.
if [ "${KIT_MUTATE:-0}" = "1" ]; then
  python3 tests/mutate_gate.py || fail "surviving mutants in kit_gate.py"
else
  printf 'skipped — set KIT_MUTATE=1 to run it (~15 min; CI runs it on every push)\n'
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
