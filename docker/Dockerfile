# The kit's own workshop. Nothing is installed on the host; uv lives here.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.8.4 /uv /uvx /usr/local/bin/

ARG UID=1000
ARG GID=1000
RUN groupadd -o -g "${GID}" kit \
 && useradd -o -u "${UID}" -g "${GID}" -m -s /bin/bash kit \
 && apt-get update \
 && apt-get install -y --no-install-recommends git ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# The virtualenv lives outside the mounted code, so the host never sees root-owned files.
ENV UV_PROJECT_ENVIRONMENT=/venv \
    UV_LINK_MODE=copy \
    UV_CACHE_DIR=/home/kit/.cache/uv \
    VIRTUAL_ENV=/venv \
    PATH="/venv/bin:/home/kit/.local/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1
RUN install -d -o "${UID}" -g "${GID}" /venv /app /home/kit/.cache/uv

USER kit
WORKDIR /app

COPY --chown=${UID}:${GID} docker/entrypoint.sh /usr/local/bin/entrypoint.sh
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["sleep", "infinity"]
