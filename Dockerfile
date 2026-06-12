# ==========================================
# Stage 1: Build virtual environment dependencies
# ==========================================
FROM python:3.11-slim as builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir poetry
COPY pyproject.toml poetry.lock* /build/
RUN poetry config virtualenvs.create false \
    && poetry install --no-root --no-interaction --no-ansi

# ==========================================
# Stage 2: Base runtime setup
# ==========================================
FROM python:3.11-slim as base-runtime

# Install postgres client libraries required for runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed dependencies and binaries from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

WORKDIR /workspace
ENV PYTHONPATH="/workspace"

# Create non-root user
RUN groupadd -g 999 ltx && \
    useradd -r -u 999 -g ltx ltx && \
    chown -R ltx:ltx /workspace

# Copy source code
COPY --chown=ltx:ltx app /workspace/app
COPY --chown=ltx:ltx migrations /workspace/migrations
COPY --chown=ltx:ltx alembic.ini /workspace/alembic.ini

# Switch to non-root user
USER ltx

# ==========================================
# Stage 3: API Target
# ==========================================
FROM base-runtime as api
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ==========================================
# Stage 4: Worker Target
# ==========================================
FROM base-runtime as worker
CMD ["celery", "-A", "app.workers.celery_app", "worker", "--loglevel=INFO", "-E"]

# ==========================================
# Stage 5: Scheduler Target
# ==========================================
FROM base-runtime as scheduler
CMD ["celery", "-A", "app.workers.celery_app", "beat", "--loglevel=INFO"]
