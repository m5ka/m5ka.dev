FROM python:3.13.13-slim-trixie

COPY --from=ghcr.io/astral-sh/uv:0.11.31 /uv /uvx /usr/local/bin/

RUN useradd -m wagtail

EXPOSE 8080

ENV PYTHONUNBUFFERED=1 \
    PORT=8080 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

RUN apt-get update --yes --quiet && apt-get install --yes --quiet --no-install-recommends \
    build-essential \
    libpq-dev \
    libjpeg62-turbo-dev \
    zlib1g-dev \
    libwebp-dev \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN chown wagtail:wagtail /app

USER wagtail
COPY --chown=wagtail:wagtail pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY --chown=wagtail:wagtail . .

CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 m5ka.core.wsgi:application
