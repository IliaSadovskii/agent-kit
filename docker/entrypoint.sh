#!/usr/bin/env bash
# Dependencies are part of `make up`, never a step a person does afterwards.
#
# `--locked` refuses to re-resolve: the committed lock is the environment, and a
# lock that has drifted says so instead of quietly becoming a different one. A
# start with no network keeps whatever the image already has rather than
# restart-looping, because a workshop that was fine yesterday is fine today.
set -euo pipefail

cd /app
if ! uv sync --locked --group dev --quiet; then
    if agent-kit --version >/dev/null 2>&1; then
        echo "entrypoint: uv sync failed; keeping the environment already installed" >&2
    else
        echo "entrypoint: uv sync failed and there is no working environment to fall back on" >&2
        exit 1
    fi
fi

exec "$@"
