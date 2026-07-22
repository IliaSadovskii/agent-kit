#!/usr/bin/env bash
#
# agent-kit installer / updater.
#
#   install.sh install [options]     install the kit into a project
#   install.sh update  [options]     update an installed kit, preserving local edits
#   install.sh status  [options]     show installed version and locally modified kit files
#   install.sh diff    [options]     diff locally modified kit files against the release
#   install.sh uninstall [options]   remove kit-owned files, keep everything user-owned
#
# Options:
#   --dir <path>        project root (default: git root of the current directory, else $PWD)
#   --ref <ref>         kit ref to install: a tag, branch, or commit (default: latest tag)
#   --from <path>       install from a local kit checkout instead of fetching
#   --repo <url>        kit repository (default: the public GitHub repo below)
#   --providers <list>  comma-separated: claude,codex (default: both, or the installed set)
#   --dry-run           print what would change, write nothing
#   --force             overwrite locally modified kit files instead of reporting a conflict
#   -h, --help          this help
#
# What is user-owned and never touched: .agent-kit/project/, product docs, source code, the
# sections of CLAUDE.md / AGENTS.md outside the kit:managed markers, and .claude/settings.local.json.

set -euo pipefail

DEFAULT_REPO="https://github.com/IliaSadovskii/agent-kit"

COMMAND=""
PROJECT_DIR=""
REF=""
FROM=""
REPO="$DEFAULT_REPO"
PROVIDERS=""
DRY_RUN=0
FORCE=0
TMP_DIR=""

# --------------------------------------------------------------------------------------------
# output helpers
# --------------------------------------------------------------------------------------------

if [ -t 1 ]; then
  C_BOLD=$'\033[1m'; C_RED=$'\033[31m'; C_YELLOW=$'\033[33m'; C_GREEN=$'\033[32m'; C_OFF=$'\033[0m'
else
  C_BOLD=""; C_RED=""; C_YELLOW=""; C_GREEN=""; C_OFF=""
fi

say()  { printf '%s\n' "$*"; }
info() { printf '%s\n' "$*"; }
warn() { printf '%swarning:%s %s\n' "$C_YELLOW" "$C_OFF" "$*" >&2; }
die()  { printf '%serror:%s %s\n' "$C_RED" "$C_OFF" "$*" >&2; exit 1; }

usage() { sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'; }

cleanup() {
  if [ -n "$TMP_DIR" ] && [ -d "$TMP_DIR" ]; then rm -rf "$TMP_DIR"; fi
}
trap cleanup EXIT

# --------------------------------------------------------------------------------------------
# argument parsing
# --------------------------------------------------------------------------------------------

parse_args() {
  case "${1:-}" in
    install|update|status|diff|uninstall) COMMAND="$1"; shift ;;
    -h|--help|"") usage; exit 0 ;;
    *) die "unknown command: $1 (expected install, update, status, diff, or uninstall)" ;;
  esac

  while [ $# -gt 0 ]; do
    case "$1" in
      --dir)       PROJECT_DIR="${2:?--dir needs a path}"; shift 2 ;;
      --ref)       REF="${2:?--ref needs a value}"; shift 2 ;;
      --from)      FROM="${2:?--from needs a path}"; shift 2 ;;
      --repo)      REPO="${2:?--repo needs a URL}"; shift 2 ;;
      --providers) PROVIDERS="${2:?--providers needs a list}"; shift 2 ;;
      --dry-run)   DRY_RUN=1; shift ;;
      --force)     FORCE=1; shift ;;
      -h|--help)   usage; exit 0 ;;
      *) die "unknown option: $1" ;;
    esac
  done

  if [ -z "$PROJECT_DIR" ]; then
    PROJECT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
  fi
  [ -d "$PROJECT_DIR" ] || die "project directory does not exist: $PROJECT_DIR"
  PROJECT_DIR="$(cd "$PROJECT_DIR" && pwd)"
}

# --------------------------------------------------------------------------------------------
# checksums
# --------------------------------------------------------------------------------------------

if command -v sha256sum >/dev/null 2>&1; then
  sha_of() { sha256sum "$1" | cut -d' ' -f1; }
elif command -v shasum >/dev/null 2>&1; then
  sha_of() { shasum -a 256 "$1" | cut -d' ' -f1; }
else
  die "need sha256sum or shasum to track kit files"
fi

# --------------------------------------------------------------------------------------------
# fetching the kit
# --------------------------------------------------------------------------------------------

latest_tag() {
  # Highest semver tag on the remote, so a plain `install` lands on a release, not on main.
  git ls-remote --tags --refs "$REPO" 2>/dev/null \
    | awk '{print $2}' | sed 's#refs/tags/##' \
    | grep -E '^v?[0-9]+\.[0-9]+\.[0-9]+$' \
    | sed 's/^v//' | sort -t. -k1,1n -k2,2n -k3,3n | tail -1 \
    | sed 's/^/v/'
}

fetch_source() {
  if [ -n "$FROM" ]; then
    [ -d "$FROM/kit" ] || die "--from path is not a kit checkout (no kit/ directory): $FROM"
    SRC="$(cd "$FROM" && pwd)"
    SRC_REF="local:$SRC"
    SRC_COMMIT="$(git -C "$SRC" rev-parse --verify --quiet HEAD 2>/dev/null || true)"
    [ -n "$SRC_COMMIT" ] || SRC_COMMIT="unknown"
    return
  fi

  command -v git >/dev/null 2>&1 || die "git is required to fetch the kit"

  if [ -z "$REF" ]; then
    REF="$(latest_tag || true)"
    [ -n "$REF" ] || {
      warn "no semver tag found in $REPO — falling back to the default branch"
      REF="HEAD"
    }
  fi

  TMP_DIR="$(mktemp -d)"
  SRC="$TMP_DIR/kit-src"
  info "Fetching $REPO @ $REF ..."
  if [ "$REF" = "HEAD" ]; then
    git clone --quiet --depth 1 "$REPO" "$SRC" || die "could not clone $REPO"
  else
    git clone --quiet --depth 1 --branch "$REF" "$REPO" "$SRC" \
      || die "could not clone $REPO at ref $REF"
  fi
  [ -d "$SRC/kit" ] || die "fetched repository has no kit/ payload"
  SRC_REF="$REF"
  SRC_COMMIT="$(git -C "$SRC" rev-parse HEAD)"
}

# --------------------------------------------------------------------------------------------
# payload selection
# --------------------------------------------------------------------------------------------

wants_claude() { case ",$PROVIDERS," in *,claude,*) return 0 ;; *) return 1 ;; esac; }
wants_codex()  { case ",$PROVIDERS," in *,codex,*)  return 0 ;; *) return 1 ;; esac; }

resolve_providers() {
  if [ -z "$PROVIDERS" ]; then
    PROVIDERS="$(lock_field providers || true)"
    [ -n "$PROVIDERS" ] || PROVIDERS="claude,codex"
  fi
  PROVIDERS="$(printf '%s' "$PROVIDERS" | tr -d ' ')"
  local part
  for part in ${PROVIDERS//,/ }; do
    case "$part" in
      claude|codex) ;;
      *) die "unknown provider: $part (expected claude or codex)" ;;
    esac
  done
}

# Files the kit owns in this project, relative to the project root. `kit/root/` is excluded: those
# are managed blocks spliced into CLAUDE.md / AGENTS.md, not standalone files.
payload_files() {
  (cd "$SRC/kit" && find . -type f ! -path './root/*' | sed 's#^\./##' | sort) | while read -r rel; do
    case "$rel" in
      .claude/*)          if wants_claude; then printf '%s\n' "$rel"; fi ;;
      .agents/*|.codex/*) if wants_codex;  then printf '%s\n' "$rel"; fi ;;
      *)                  printf '%s\n' "$rel" ;;
    esac
  done
}

# --------------------------------------------------------------------------------------------
# lock file — .agent-kit/kit.lock
# --------------------------------------------------------------------------------------------

LOCK() { printf '%s/.agent-kit/kit.lock' "$PROJECT_DIR"; }

lock_field() {
  local key="$1" lock; lock="$(LOCK)"
  [ -f "$lock" ] || return 1
  sed -n "s/^${key}: \{1,\}//p" "$lock" | head -1
}

# sha recorded for a file at install time, empty when the kit does not know the file
lock_sha() {
  local rel="$1" lock; lock="$(LOCK)"
  [ -f "$lock" ] || return 0
  awk -v want="  $rel: " 'index($0, want) == 1 { print substr($0, length(want) + 1); exit }' "$lock"
}

lock_files() {
  local lock; lock="$(LOCK)"
  [ -f "$lock" ] || return 0
  awk '/^files:/ { infiles = 1; next } infiles && /^  / { sub(/:.*$/, "", $1); print $1 }' "$lock"
}

write_lock() {
  local version="$1"; shift
  local lock; lock="$(LOCK)"
  {
    printf '# Generated by the agent-kit installer. Do not edit by hand.\n'
    printf '# `install.sh update` uses these checksums to tell an untouched kit file from one you\n'
    printf '# edited locally, so your edits are never silently overwritten.\n'
    printf 'kit_version: %s\n' "$version"
    printf 'source: %s\n' "$REPO"
    printf 'ref: %s\n' "$SRC_REF"
    printf 'commit: %s\n' "$SRC_COMMIT"
    printf 'installed_at: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf 'providers: %s\n' "$PROVIDERS"
    printf 'files:\n'
    local rel
    for rel in "$@"; do
      printf '  %s: %s\n' "$rel" "$(sha_of "$PROJECT_DIR/$rel")"
    done
  } > "$lock"
}

# --------------------------------------------------------------------------------------------
# managed blocks in CLAUDE.md / AGENTS.md
# --------------------------------------------------------------------------------------------

MARK_START='<!-- kit:managed:start — a kit update replaces everything between these markers. Do not hand-edit. -->'
MARK_END='<!-- kit:managed:end -->'

# Replace the managed block in $1 with the content of $2, or prepend it when the file has no
# markers yet (an existing project file keeps everything it already had).
splice_block() {
  local target="$1" block="$2" tmp
  tmp="$(mktemp)"

  if grep -qF 'kit:managed:start' "$target" && grep -qF 'kit:managed:end' "$target"; then
    awk -v start="kit:managed:start" -v end="kit:managed:end" -v blockfile="$block" \
        -v mark_start="$MARK_START" -v mark_end="$MARK_END" '
      index($0, start) { print mark_start; while ((getline line < blockfile) > 0) print line;
                         print mark_end; skipping = 1; next }
      index($0, end)   { skipping = 0; next }
      !skipping        { print }
    ' "$target" > "$tmp"
  else
    { printf '%s\n' "$MARK_START"
      cat "$block"
      printf '%s\n\n' "$MARK_END"
      cat "$target"
    } > "$tmp"
    warn "$(basename "$target") had no kit markers — the managed block was prepended, your content kept."
  fi

  if cmp -s "$tmp" "$target"; then
    rm -f "$tmp"
    return 1  # unchanged
  fi
  if [ "$DRY_RUN" -eq 1 ]; then rm -f "$tmp"; return 0; fi
  mv "$tmp" "$target"
}

# --------------------------------------------------------------------------------------------
# shared JSON config (.claude/settings.json, .codex/hooks.json)
# --------------------------------------------------------------------------------------------

HOOK_CMD='"$(git rev-parse --show-toplevel)/.agent-kit/scripts/session-setup.sh"'

# These files are shared with the project: the kit only guarantees its SessionStart hook is
# present, and never rewrites hooks or permissions the project added itself.
ensure_hook() {
  local target="$1" template="$2"

  if [ ! -f "$target" ]; then
    if [ "$DRY_RUN" -eq 0 ]; then mkdir -p "$(dirname "$target")"; cp "$template" "$target"; fi
    say "  create   ${target#"$PROJECT_DIR"/}"
    return
  fi

  if grep -qF 'session-setup.sh' "$target"; then
    return
  fi

  if ! command -v python3 >/dev/null 2>&1; then
    warn "${target#"$PROJECT_DIR"/} exists and has no kit SessionStart hook; add it manually (python3 not available for merging)"
    return
  fi

  if [ "$DRY_RUN" -eq 1 ]; then
    say "  merge    ${target#"$PROJECT_DIR"/} (kit SessionStart hook)"
    return
  fi

  python3 - "$target" "$HOOK_CMD" <<'PY' || die "could not merge the kit hook into $target"
import json, sys

path, command = sys.argv[1], sys.argv[2]
with open(path, encoding="utf-8") as fh:
    data = json.load(fh)

hooks = data.setdefault("hooks", {})
entries = hooks.setdefault("SessionStart", [])
entries.append({
    "matcher": "startup|resume",
    "hooks": [{"type": "command", "command": command}],
})

with open(path, "w", encoding="utf-8") as fh:
    json.dump(data, fh, indent=2, ensure_ascii=False)
    fh.write("\n")
PY
  say "  merge    ${target#"$PROJECT_DIR"/} (kit SessionStart hook)"
}

# --------------------------------------------------------------------------------------------
# install / update
# --------------------------------------------------------------------------------------------

CONFLICTS=()

apply_payload() {
  local installed=() rel src dest current recorded
  local n_new=0 n_upd=0 n_same=0

  while read -r rel; do
    [ -n "$rel" ] || continue
    src="$SRC/kit/$rel"
    dest="$PROJECT_DIR/$rel"
    installed+=("$rel")

    if [ ! -f "$dest" ]; then
      if [ "$DRY_RUN" -eq 0 ]; then mkdir -p "$(dirname "$dest")"; cp "$src" "$dest"; fi
      say "  create   $rel"
      n_new=$((n_new + 1))
      continue
    fi

    if cmp -s "$src" "$dest"; then
      n_same=$((n_same + 1))
      continue
    fi

    current="$(sha_of "$dest")"
    recorded="$(lock_sha "$rel")"

    if { [ -n "$recorded" ] && [ "$current" = "$recorded" ]; } || [ "$FORCE" -eq 1 ]; then
      # Untouched since the last install (or --force): safe to replace.
      if [ "$DRY_RUN" -eq 0 ]; then cp "$src" "$dest"; fi
      say "  update   $rel"
      n_upd=$((n_upd + 1))
    else
      # Locally modified, or predates the lock: keep the local file, park the new one beside it.
      if [ "$DRY_RUN" -eq 0 ]; then cp "$src" "$dest.kit-new"; fi
      say "  ${C_YELLOW}conflict${C_OFF} $rel (kept yours; release copy at $rel.kit-new)"
      CONFLICTS+=("$rel")
    fi
  done < <(payload_files)

  # Files this project got from an older release that the new one no longer ships.
  local known
  while read -r known; do
    [ -n "$known" ] || continue
    case " ${installed[*]} " in *" $known "*) continue ;; esac
    dest="$PROJECT_DIR/$known"
    [ -f "$dest" ] || continue
    current="$(sha_of "$dest")"
    recorded="$(lock_sha "$known")"
    if [ "$current" = "$recorded" ] || [ "$FORCE" -eq 1 ]; then
      if [ "$DRY_RUN" -eq 0 ]; then rm -f "$dest"; fi
      say "  remove   $known (no longer part of the kit)"
    else
      warn "$known was dropped from the kit but you modified it — leaving it in place"
    fi
  done < <(lock_files)

  INSTALLED_FILES=("${installed[@]}")
  info ""
  info "Payload: $n_new created, $n_upd updated, $n_same already current, ${#CONFLICTS[@]} conflicts."
}

install_templates() {
  local rel dest
  while read -r rel; do
    [ -n "$rel" ] || continue
    case "$rel" in
      CLAUDE.md|.claude/*) if ! wants_claude; then continue; fi ;;
      AGENTS.md|.codex/*)  if ! wants_codex;  then continue; fi ;;
    esac
    # Hook configs are merged, not copied wholesale.
    case "$rel" in .claude/settings.json|.codex/hooks.json) continue ;; esac

    dest="$PROJECT_DIR/$rel"
    if [ -e "$dest" ]; then
      continue  # user-owned: never overwritten, not even by --force
    fi
    if [ "$DRY_RUN" -eq 0 ]; then
      mkdir -p "$(dirname "$dest")"
      cp "$SRC/templates/$rel" "$dest"
    fi
    say "  create   $rel (template, yours from now on)"
  done < <(cd "$SRC/templates" && find . -type f | sed 's#^\./##' | sort)
}

apply_managed_blocks() {
  if wants_claude && [ -f "$PROJECT_DIR/CLAUDE.md" ]; then
    if splice_block "$PROJECT_DIR/CLAUDE.md" "$SRC/kit/root/CLAUDE.block.md"; then
      say "  managed  CLAUDE.md"
    fi
  fi
  if wants_codex && [ -f "$PROJECT_DIR/AGENTS.md" ]; then
    if splice_block "$PROJECT_DIR/AGENTS.md" "$SRC/kit/root/AGENTS.block.md"; then
      say "  managed  AGENTS.md"
    fi
  fi
}

sync_manifest_version() {
  local manifest="$PROJECT_DIR/.agent-kit/project/manifest.yml" version="$1"
  [ -f "$manifest" ] || return 0
  grep -q '^kit_version:' "$manifest" || return 0
  if [ "$DRY_RUN" -eq 1 ]; then return 0; fi
  sed -i.bak "s/^kit_version:.*/kit_version: $version/" "$manifest"
  rm -f "$manifest.bak"
}

ensure_gitignore() {
  local gitignore="$PROJECT_DIR/.gitignore"
  if ! wants_claude; then return 0; fi
  if grep -qF '.claude/settings.local.json' "$gitignore" 2>/dev/null; then return 0; fi
  if [ "$DRY_RUN" -eq 0 ]; then
    printf '\n# Personal Claude Code settings — never shared\n.claude/settings.local.json\n' \
      >> "$gitignore"
  fi
  say "  append   .gitignore (.claude/settings.local.json)"
}

do_install() {
  local mode="$1" version
  fetch_source
  resolve_providers
  version="$(cat "$SRC/VERSION" 2>/dev/null || echo unknown)"

  if [ "$mode" = "install" ] && [ -f "$(LOCK)" ]; then
    info "This project already has agent-kit $(lock_field kit_version). Running an update instead."
    mode="update"
  fi
  if [ "$mode" = "update" ] && [ ! -f "$(LOCK)" ]; then
    warn "no .agent-kit/kit.lock found — treating existing kit files as locally modified"
  fi

  info ""
  info "${C_BOLD}agent-kit $version → $PROJECT_DIR${C_OFF}  (providers: $PROVIDERS)"
  if [ "$DRY_RUN" -eq 1 ]; then info "${C_YELLOW}dry run — nothing will be written${C_OFF}"; fi
  info ""

  apply_payload
  install_templates
  apply_managed_blocks
  if wants_claude; then
    ensure_hook "$PROJECT_DIR/.claude/settings.json" "$SRC/templates/.claude/settings.json"
  fi
  if wants_codex; then
    ensure_hook "$PROJECT_DIR/.codex/hooks.json" "$SRC/templates/.codex/hooks.json"
  fi
  ensure_gitignore
  sync_manifest_version "$version"

  if [ "$DRY_RUN" -eq 0 ]; then
    write_lock "$version" "${INSTALLED_FILES[@]}"
    chmod +x "$PROJECT_DIR/.agent-kit/scripts/"*.sh 2>/dev/null || true
  fi

  info ""
  if [ ${#CONFLICTS[@]} -gt 0 ]; then
    printf '%s%d file(s) you had modified were kept.%s Review and merge:\n\n' \
      "$C_YELLOW" "${#CONFLICTS[@]}" "$C_OFF"
    local rel
    for rel in "${CONFLICTS[@]}"; do
      printf '  diff -u %s %s.kit-new\n' "$rel" "$rel"
    done
    printf '\nWhen done, delete the .kit-new files and re-run `install.sh update` to refresh the lock.\n\n'
  fi

  if [ -f "$SRC/migrations/$version.md" ]; then
    info "${C_BOLD}Migration notes for $version:${C_OFF} see migrations/$version.md in the kit repo."
    info ""
  fi

  say "${C_GREEN}Done.${C_OFF} Next:"
  say "  1. Review the diff and commit — the kit belongs in version control."
  say "  2. Start a fresh Claude Code / Codex session so the new skills are discovered."
  if [ ! -f "$PROJECT_DIR/.agent-kit/project/manifest.yml" ] \
     || grep -q '^bootstrapped: false' "$PROJECT_DIR/.agent-kit/project/manifest.yml" 2>/dev/null; then
    say "  3. Run /go (Claude Code) or \$go (Codex) — it will bootstrap the project."
  fi
}

# --------------------------------------------------------------------------------------------
# status / diff / uninstall
# --------------------------------------------------------------------------------------------

modified_files() {
  local rel recorded current
  while read -r rel; do
    [ -n "$rel" ] || continue
    [ -f "$PROJECT_DIR/$rel" ] || { printf 'missing %s\n' "$rel"; continue; }
    recorded="$(lock_sha "$rel")"
    current="$(sha_of "$PROJECT_DIR/$rel")"
    [ "$recorded" = "$current" ] || printf 'modified %s\n' "$rel"
  done < <(lock_files)
}

do_status() {
  [ -f "$(LOCK)" ] || die "no kit installed here (.agent-kit/kit.lock not found)"
  say "${C_BOLD}agent-kit $(lock_field kit_version)${C_OFF}"
  say "  source:    $(lock_field source)"
  say "  ref:       $(lock_field ref)  (commit $(lock_field commit))"
  say "  installed: $(lock_field installed_at)"
  say "  providers: $(lock_field providers)"
  say "  files:     $(lock_files | wc -l | tr -d ' ')"

  local changes; changes="$(modified_files)"
  if [ -n "$changes" ]; then
    say ""
    say "${C_YELLOW}Locally modified kit files${C_OFF} (an update will keep these and park the release copy):"
    printf '%s\n' "$changes" | sed 's/^/  /'
    say ""
    say "Local edits to kit-owned files drift away from the released kit. Consider upstreaming"
    say "them to $(lock_field source), or moving them to .agent-kit/project/instructions.md."
  else
    say ""
    say "${C_GREEN}No local modifications to kit files.${C_OFF}"
  fi

  if [ -z "$FROM" ]; then
    local latest; latest="$(latest_tag || true)"
    if [ -n "$latest" ] && [ "$latest" != "$(lock_field ref)" ]; then
      say ""
      say "Latest release: ${C_BOLD}$latest${C_OFF} — run: install.sh update"
    fi
  fi
}

do_diff() {
  [ -f "$(LOCK)" ] || die "no kit installed here (.agent-kit/kit.lock not found)"
  fetch_source
  local rel status
  while read -r status rel; do
    [ "$status" = "modified" ] || continue
    [ -f "$SRC/kit/$rel" ] || continue
    printf '%s=== %s ===%s\n' "$C_BOLD" "$rel" "$C_OFF"
    diff -u "$SRC/kit/$rel" "$PROJECT_DIR/$rel" || true
  done < <(modified_files)
}

do_uninstall() {
  [ -f "$(LOCK)" ] || die "no kit installed here (.agent-kit/kit.lock not found)"
  local rel
  while read -r rel; do
    [ -n "$rel" ] || continue
    [ "$DRY_RUN" -eq 1 ] || rm -f "$PROJECT_DIR/$rel"
    say "  remove   $rel"
  done < <(lock_files)
  [ "$DRY_RUN" -eq 1 ] || rm -f "$(LOCK)"
  say ""
  say "Removed kit-owned files. Left untouched, for you to clean up or keep:"
  say "  .agent-kit/project/, CLAUDE.md, AGENTS.md, .claude/settings.json, .codex/hooks.json"
  say "  (the managed blocks in CLAUDE.md / AGENTS.md now import files that are gone — drop them)"
}

# --------------------------------------------------------------------------------------------

main() {
  parse_args "$@"
  case "$COMMAND" in
    install|update) do_install "$COMMAND" ;;
    status)         do_status ;;
    diff)           do_diff ;;
    uninstall)      do_uninstall ;;
  esac
}

main "$@"
