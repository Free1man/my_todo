# Runtime image
FROM python:3.12-slim

# System deps (for bcrypt wheels & general build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
 && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install Python deps first (layer caching)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy source
COPY app /app/app

# (No explicit data volume; devcontainer will bind mount the workspace at /app)

# Sensible defaults (can be overridden by .env)
ENV DATA_DIR=/app/data \
    ACCESS_TOKEN_EXPIRE_MINUTES=60

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
