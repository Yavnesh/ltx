# LTX Video Generation Platform

A production-grade, highly scalable, asynchronous video generation platform built around the LTX Video model. Swappable between mock generation and GPU-enabled LTX inference.

## Architecture

```
Client -> FastAPI Gateway -> Redis (Rate limiting / Celery Broker)
              |
              +-> PostgreSQL (User & Job State tracking)
              |
           Celery Worker (LTX Model video generation)
              |
              +-> MinIO / S3 (Object Storage)
```

## Features

- **Asynchronous Task Queue**: Uses Celery to run video generation in background workers.
- **Dynamic Storage Provider**: Swaps between local file storage, local MinIO container, or production AWS S3 via config.
- **Dynamic Model Generation**: Supports CPU/memory-light mock generation for local dev, or actual diffusers LTX Video pipeline for production GPU execution.
- **Robust State Machine**: Enforces strict status transitions (`QUEUED` -> `PROCESSING` -> `COMPLETED`/`FAILED` or `QUEUED` -> `CANCELLED`).
- **Observability**: Prometheus metrics (`/metrics`), structured JSON logging (`structlog`), and OpenTelemetry tracing (Jaeger/OTLP).
- **Security & Scalability**: Built-in sliding-window Redis rate limiting (100 req/hr/user) and JWT token validation.

---

## Directory Structure

```
ltx-platform/
├── app/
│   ├── api/             # Routes (Auth, Videos, Health) & Middleware
│   ├── infrastructure/  # DB connections, Security, OTEL, Storage & Generator Providers
│   ├── repositories/    # Database CRUD (User, Job)
│   ├── services/        # Business logic layer (Job, Video, Storage, User)
│   ├── workers/         # Celery app & tasks
│   └── main.py          # FastAPI application entrypoint
├── docker/              # Prometheus and Grafana config scripts
├── migrations/          # Alembic migrations (tables setup)
├── tests/               # Pytest suite (unit, integration, task tests)
├── Dockerfile           # Multi-stage build (api, worker, scheduler)
├── docker-compose.yml   # Dev services configuration
├── Makefile             # Automation wrapper
├── pyproject.toml       # Python dependencies
└── README.md
```

---

## Quick Start

Ensure Docker and Docker Compose are installed.

### 1. Build and Start the Stack

```bash
make up
```

This starts:
- PostgreSQL (Port 5432)
- Redis (Port 6379)
- MinIO (Port 9000 API, Port 9001 Console)
- Jaeger (Port 16686 UI, Port 4317 OTLP)
- Prometheus (Port 9090)
- Grafana (Port 3000)
- API gateway (Port 8000)
- Celery worker
- Celery scheduler

### 2. Apply Database Migrations

Inside the API container, or locally if poetry is configured:
```bash
docker compose exec api alembic upgrade head
```

---

## API Testing Guide

### 1. Register a User
```bash
curl -X POST http://localhost:8000/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "securepassword123"}'
```

### 2. Retrieve JWT Auth Token
```bash
curl -X POST http://localhost:8000/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "securepassword123"}'
```
Response:
```json
{
  "access_token": "YOUR_JWT_TOKEN",
  "token_type": "bearer"
}
```

### 3. Submit a Video Generation Job
```bash
curl -X POST http://localhost:8000/v1/videos \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "astronaut riding a horse on mars",
    "duration": 5,
    "resolution": "720p",
    "fps": 24,
    "seed": 123
  }'
```
Response:
```json
{
  "job_id": "uuid-string",
  "status": "QUEUED"
}
```

### 4. Check status
```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  http://localhost:8000/v1/videos/<job_id>
```

### 5. List Jobs (Supports sorting, pagination, filtering)
```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:8000/v1/videos?status=COMPLETED&limit=10&offset=0"
```
