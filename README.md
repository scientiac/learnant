# Multi-Tenant Learning Platform

Small Django application for a secure multi-tenant learning platform.

## Local setup

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_demo
.venv/bin/python manage.py runserver
```

Visit `http://127.0.0.1:8000/` and log in with a demo user.

The UI uses Django templates with minimal HTML plus Tailwind/HTMX CDN links. The current working pages are login, dashboard, course list/create, lesson list/create, and tenant-admin course assignment.

Demo users created by `seed_demo`:

| Username | Role | Password |
| --- | --- | --- |
| `superadmin` | Super Admin | `password123` |
| `admin` | Admin | `password123` |
| `viewer` | Super Viewer | `password123` |
| `tenantadmin` | Tenant Admin | `password123` |
| `learner` | Tenant User | `password123` |

The health check is available at `http://127.0.0.1:8000/health/`.

After running `seed_demo`, log in as `tenantadmin` and open `http://127.0.0.1:8000/courses/` to see the sample course list. Tenant admins with an active tenant can create courses, lessons, and assign tenant learners. The seeded `learner` account is assigned to the sample course.

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
