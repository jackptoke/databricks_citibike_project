# Streamlit executive dashboard — deployable to Railway (or any container host).
FROM python:3.12-slim

# uv for fast, reproducible installs from the lockfile.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
ENV UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Install dependencies first (from the lockfile) for better layer caching.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

# Railway injects $PORT at runtime; default to 8080 for local `docker run`.
ENV PORT=8080
EXPOSE 8080

# Run via the project venv created by `uv sync`. Shell form so $PORT expands.
CMD .venv/bin/streamlit run app.py \
    --server.port ${PORT} \
    --server.address 0.0.0.0 \
    --server.headless true
