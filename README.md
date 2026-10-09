# Multi-Tenant Learning Platform

Small Django application for a secure multi-tenant learning platform.

## Local setup

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver
```

Visit `http://127.0.0.1:8000/` for the health check.

## Configuration

Copy `.env.example` to `.env` if desired and export the values before running Django. PostgreSQL is the target database for the completed app. If `POSTGRES_DB` is not set, local development uses SQLite.

No real secrets should be committed.

## Tests

```bash
.venv/bin/python manage.py test
.venv/bin/python manage.py check
```

## Authorization policy

The initial role and expired-tenant access policy is documented in `docs/permissions.md`.
