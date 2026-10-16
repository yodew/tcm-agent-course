FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY knowledge ./knowledge
COPY migrations ./migrations
COPY alembic.ini ./
RUN uv sync --frozen --no-dev && useradd --uid 10001 --create-home app && mkdir /app/data && chown app /app/data
USER app
EXPOSE 8000
CMD ["uv", "run", "--no-sync", "tcm", "serve", "--host", "0.0.0.0"]
