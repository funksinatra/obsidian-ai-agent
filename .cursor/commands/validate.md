---
description: Run full local validation for tests, types, lint, server, and Docker
---

# Validate Project

Run comprehensive validation of the project to ensure tests, type checks, linting, and deployment are working correctly.

Execute the following commands in sequence and report results.

## 1. Test Suite

```bash
uv run pytest -v
```

Expected: all tests pass.

## 2. Type Checking

```bash
uv run mypy app/
uv run pyright app/
```

Expected:
- mypy reports no issues
- pyright reports `0 errors`

## 3. Linting

```bash
uv run ruff check .
```

Expected: all checks pass.

## 4. Local Server Validation

Start the server in background:

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8123
```

After startup, validate endpoints:

```bash
curl -s http://localhost:8123/ | python3 -m json.tool
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://localhost:8123/docs
curl -s http://localhost:8123/health | python3 -m json.tool
curl -s http://localhost:8123/health/db | python3 -m json.tool
```

Expected:
- root endpoint returns app metadata JSON
- docs endpoint returns `HTTP Status: 200`
- health endpoints return `{"status":"healthy"}`

Stop the local server when done (Ctrl+C if foreground, or terminate process if backgrounded).

## 5. Docker Deployment Validation

Build and start services:

```bash
docker-compose up -d --build
docker-compose ps
```

Expected: `db` and `app` are up.

Validate endpoints through Docker:

```bash
curl -s http://localhost:8123/ | python3 -m json.tool
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://localhost:8123/docs
curl -s http://localhost:8123/health | python3 -m json.tool
curl -s http://localhost:8123/health/db | python3 -m json.tool
```

Inspect logs:

```bash
docker-compose logs app
```

Expected: structured logs with request correlation and startup events.

Stop services:

```bash
docker-compose down
```

## 6. Summary Report

Provide a final report with:
- tests passed/failed
- mypy status
- pyright status
- linting status
- local server validation status
- Docker validation status
- errors or warnings encountered
- overall health assessment: `PASS` or `FAIL`
