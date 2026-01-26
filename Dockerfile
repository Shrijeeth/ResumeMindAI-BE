# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# System deps (minimal) and uv for lockfile-aware installs
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential git \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv

# Install dependencies using the lockfile
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --compile-bytecode

# Copy application code
COPY . .

EXPOSE 8000

CMD ["sh", "-c", "uv run alembic upgrade head && NEW_RELIC_CONFIG_FILE=newrelic.ini newrelic-admin run-program uv run main.py"]
