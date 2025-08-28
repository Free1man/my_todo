# Runtime image
FROM python:3.12-slim

# System deps (for bcrypt wheels & general build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
 && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install Poetry and dependencies first for better layer caching
ENV POETRY_HOME=/opt/poetry \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    PATH="/opt/poetry/bin:${PATH}"

RUN curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s ${POETRY_HOME}/bin/poetry /usr/local/bin/poetry

# Copy only pyproject first to leverage caching
COPY pyproject.toml /app/pyproject.toml
RUN poetry install --no-root --only main

# Copy source
COPY app /app/app

# (No explicit data volume; devcontainer will bind mount the workspace at /app)

# Sensible defaults (can be overridden by .env)
ENV DATA_DIR=/app/data \
    ACCESS_TOKEN_EXPIRE_MINUTES=60

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
