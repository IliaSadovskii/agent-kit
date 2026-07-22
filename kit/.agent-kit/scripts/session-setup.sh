#!/usr/bin/env bash
set -u

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
PROJECT_SETUP="$ROOT/scripts/cloud-setup.sh"

# A fresh project may not have been bootstrapped yet. Missing setup is intentionally non-fatal;
# idea-interview will create an appropriate project-owned script.
[ -f "$PROJECT_SETUP" ] || exit 0

exec bash "$PROJECT_SETUP"
