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
# not having it, and the command list is what a reader decides on. They head each command with
# `### \`name …\``, not with the `/agent-kit:` form — so the earlier version of this check compared
# two empty lists and passed for as long as it existed, while the storefront called `fix` unwritten
# and never mentioned `next` at all.
heads() { grep -oE '^### `[a-z-]+' "$1" | sed 's/^### `//' | sort -u; }
en="$(heads README.md)"
ru="$(heads README.ru.md)"
[ -n "$en" ] || fail "README.md documents no commands — the heading form this check reads has changed"
[ "$en" = "$ru" ] || fail "README.md and README.ru.md document different commands"

# The command list is not where they actually drift: a row went missing from one *table* and the
# check above was happy, because both files still named seven commands. Structure is the cheapest
# proxy — same sections, same number of table rows.
for shape in '^## ' '^| '; do
  a="$(grep -c "$shape" README.md)"
  b="$(grep -c "$shape" README.ru.md)"
  [ "$a" = "$b" ] || fail "README.md and README.ru.md differ in structure: $a vs $b lines matching '$shape'"
done

# And the front door must agree with what ships. A command missing from it is one nobody finds; a
# command it still calls unwritten is worse, because the reader believes it.
for path in "$PLUGIN"/skills/*/; do
  name="$(basename "$path")"
  printf '%s\n' "$en" | grep -qx "$name" || fail "README.md does not document /agent-kit:$name"
done
for name in $en; do
  [ -d "$PLUGIN/skills/$name" ] || fail "README.md documents $name, which is not a skill"
  stub_readme="$(grep -hE "^### \`$name\b.*(not written|не написана)" README.md README.ru.md | wc -l)"
  if grep -q "Not written yet." "$PLUGIN/skills/$name/SKILL.md"; then
    [ "$stub_readme" -eq 2 ] || fail "$name is a stub; both READMEs must say so in its heading"
  else
    [ "$stub_readme" -eq 0 ] || fail "$name is written, and a README still calls it unwritten"
  fi
done

# --------------------------------------------------------------------------------------------
step "internal references resolve"

# Every ${CLAUDE_PLUGIN_ROOT}/... path the payload mentions must exist in it.
while IFS= read -r ref; do
  [ -e "$PLUGIN/${ref}" ] || fail "dangling reference: \${CLAUDE_PLUGIN_ROOT}/$ref"
done < <(grep -rhoE '\$\{CLAUDE_PLUGIN_ROOT\}/[A-Za-z0-9_./-]+' "$PLUGIN" \
           | sed 's|${CLAUDE_PLUGIN_ROOT}/||' | sed 's|[.,)]*$||' | sort -u)

# --------------------------------------------------------------------------------------------
step "both hooks are registered and run"

# A hook that is not registered is a rule the payload believes in and nothing enforces — the exact
# shape the audit refused to ship. So the registration is checked, not assumed. Every file under
# hooks/ must be registered too: one added and never wired in would look like protection.
python3 -c "
import json, pathlib, sys
spec = json.load(open('$PLUGIN/hooks/hooks.json'))
events = spec.get('hooks') or {}
for event in ('PreToolUse', 'Stop'):
    if event not in events:
        sys.exit('hooks.json registers no ' + event + ' hook')
wired = json.dumps(events)
for path in pathlib.Path('$PLUGIN/hooks').glob('*.py'):
    if path.name not in wired:
        sys.exit(path.name + ' is not registered in hooks.json')
" || fail "hooks.json is missing, or a hook in hooks/ is not registered"

# Each must survive being asked about something it has no opinion on, with no run in flight.
printf '{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"echo hi\"},\"cwd\":\"/\"}' \
  | python3 "$PLUGIN/hooks/guard.py" >/dev/null 2>&1 || fail "the guard failed on a harmless command"
printf '{\"hook_event_name\":\"Stop\",\"cwd\":\"/\"}' \
  | python3 "$PLUGIN/hooks/stop.py" >/dev/null 2>&1 || fail "the stop hook failed outside a project"

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
step "every durable file the payload names has a row in the channel table"

# `rules/channels.md` says every mechanism arrives with four answers — who writes it, who reads it,
# who may close it, and what becomes impossible without it — and it is the table of those answers.
# Nothing held the table to the payload, so a command could start writing a file and the table would
# not know: `docs/advice/`, `docs/knowledge/` and `.agent-kit/project.yml` were all being written and
# read with no row, and this check is what found them.
#
# The unit is the family — `docs/runs`, `docs/audits` — not the exact path, because the payload
# writes `<lens>` and `<slug>` where a project has a name. Three families are named in the script as
# not being channels at all, each with its reason; a fourth is not added without one.
python3 - "$REPO" "$PLUGIN" <<'PY'
import re, sys
from pathlib import Path

root = Path(sys.argv[1]) / sys.argv[2]

NOT_CHANNELS = {
    "docs/design": "the kit's own design notes; no project a user runs this on has them",
    "docs/DEVELOPER.md": "an example of the owner's own document, the one a `source:` points at",
    "docs/advise-<date>": "a git branch `advise` opens, not a path — the only one of these that is",
}

PATH_RE = re.compile(r"(?:docs|\.agent-kit)/[A-Za-z0-9_.<>*{}-]+(?:/[A-Za-z0-9_.<>*{}-]+)*")


def family(text):
    parts = text.rstrip(".,;:)`").split("/")
    return "/".join(parts[:2]) if len(parts) > 1 else parts[0]


# What the table declares, read from the first cell of each row and from nowhere else. Against the
# whole file, `docs/audit` — the singular typo this pair of checks exists to catch — would match
# the row for `docs/audits/<lens>.md`, and a family named only in a prose bullet or in another
# row's Lives column would read as though it had a row of its own.
declared = set()
for line in (root / "rules" / "channels.md").read_text(encoding="utf-8").splitlines():
    if not line.startswith("|"):
        continue
    cell = line.split("|")[1]
    declared.update(family(found) for found in PATH_RE.findall(cell))

errors, seen = [], {}
for path in sorted(root.rglob("*")):
    if not path.is_file() or path.suffix not in (".md", ".py", ".json", ".yml"):
        continue
    if "__pycache__" in path.parts:
        continue
    for found in PATH_RE.findall(path.read_text(encoding="utf-8", errors="replace")):
        seen.setdefault(family(found), path.relative_to(root))

for name, where in sorted(seen.items()):
    if name in NOT_CHANNELS or name in declared:
        continue
    errors.append(f"{name} is written or read by the payload ({where}) and has no row in "
                  f"rules/channels.md — a file with no writer, reader and closer named is not a "
                  f"mechanism yet")

for e in errors:
    print(f"ERROR: {e}", file=sys.stderr)
sys.exit(1 if errors else 0)
PY
[ $? -eq 0 ] || fail "a file the payload names is not in the channel table"

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

errors = []
# Both records the kit ships a shape for: the run file, which dies with the machine, and the batch
# record, which is all of a batch that outlives it. The same rule holds for each.
records = {name: root / "templates" / name for name in ("run.json", "batch.json")}
for name, template in records.items():
    shape = json.loads(template.read_text(encoding="utf-8"))

    # Both templates are out of the payload, not just the one under test. They share eleven field
    # names — `slug`, `command`, `pr`, `spent` — so leaving the other in would let the two vouch
    # for each other and a field whose last real reader was deleted would still count two sides.
    payload = [p for p in sorted(root.rglob("*"))
               if p.is_file() and p.suffix in (".md", ".py", ".json", ".yml")
               and p not in records.values() and "__pycache__" not in p.parts]
    texts = {p: p.read_text(encoding="utf-8", errors="replace") for p in payload}

    for field in [k for k in shape if not k.startswith("_")]:
        named = [p for p, text in texts.items() if re.search(rf"\b{re.escape(field)}\b", text)]
        if len(named) < 2:
            where = ", ".join(str(p.relative_to(root)) for p in named) or "nowhere"
            errors.append(f"{name} field {field!r} is named in {where} — a record with one side "
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
  python3 -m compileall -q "$PLUGIN/scripts" "$PLUGIN/hooks" >/dev/null \
    || fail "python syntax error under $PLUGIN/scripts or $PLUGIN/hooks"
  python3 -m unittest discover -s tests -q || fail "tests failed"
fi

# --------------------------------------------------------------------------------------------
step "shell syntax"

# CI has shellcheck and a developer's machine often does not, so a silent skip means the local run
# says OK for a different set of checks than the one that gates the release. It cost eight red runs
# in a row before anyone read the log.
if ! command -v shellcheck >/dev/null 2>&1; then
  printf 'NOTE: shellcheck is not installed here — CI runs it, so this check is untested locally.\n'
fi

while IFS= read -r sh; do
  bash -n "$sh" || fail "syntax error: $sh"
  if command -v shellcheck >/dev/null 2>&1; then
    shellcheck -S warning "$sh" || fail "shellcheck: $sh"
  fi
done < <(find "$PLUGIN" scripts -name '*.sh' 2>/dev/null)

# --------------------------------------------------------------------------------------------
printf '\n'
if [ "$errors" -eq 0 ]; then
  printf 'OK — %s %s validates\n' "$PLUGIN" "$VERSION"
else
  printf '%d error(s)\n' "$errors" >&2
fi
exit $(( errors > 0 ))
