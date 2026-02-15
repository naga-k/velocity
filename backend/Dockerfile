FROM python:3.12-slim

WORKDIR /app

# Install git (needed for SDK fork dependency) and clean up
# Note: Node.js and claude-code CLI now run inside Daytona sandboxes, not in this container
RUN apt-get update && \
    apt-get install -y git && \
    rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies (no dev deps in production)
RUN uv sync --frozen --no-dev

# Copy application code
COPY app/ app/

# Note: memory/ directory not copied - agents now run in Daytona sandboxes

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
