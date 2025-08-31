# Runtime image
FROM python:3.12-slim

# System deps (general build tools and curl for Poetry installer)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
 && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Build-time switch: set to true for production, false for dev/test
ARG PROD=true

# Install Poetry and dependencies first for better layer caching
ENV POETRY_HOME=/opt/poetry \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    PATH="/opt/poetry/bin:${PATH}"

RUN curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s ${POETRY_HOME}/bin/poetry /usr/local/bin/poetry

# Copy only pyproject (and lock) first to leverage caching
COPY pyproject.toml /app/pyproject.toml
COPY poetry.lock /app/poetry.lock
# Ensure lock file metadata matches current Poetry version/format
RUN poetry lock
# Install dependencies: only main in PROD, with dev tools otherwise
RUN if [ "$PROD" = "true" ]; then \
            poetry install --no-root --only main; \
        else \
            poetry install --no-root --with dev; \
        fi

# Copy source
COPY backend /app/backend
COPY static /app/static

# Optionally include tests in non-prod builds
COPY tests /app/tests
RUN if [ "$PROD" = "true" ]; then rm -rf /app/tests; fi

EXPOSE 8000
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
