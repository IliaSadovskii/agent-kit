#!/usr/bin/env bash
# Dependencies are part of `make up`, never a step a person does afterwards.
set -euo pipefail

cd /app
uv sync --group dev --quiet
exec "$@"
