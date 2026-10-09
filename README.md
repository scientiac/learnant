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

The UI uses Django templates with minimal HTML plus Tailwind/HTMX CDN links. The current working pages are login, dashboard, course list/create, lesson list/create, tenant-admin course assignment, learner lesson completion, and tenant-admin progress viewing.

Demo users created by `seed_demo`:

| Username | Role | Password |
| --- | --- | --- |
| `superadmin` | Super Admin | `password123` |
| `admin` | Admin | `password123` |
| `viewer` | Super Viewer | `password123` |
| `tenantadmin` | Tenant Admin | `password123` |
| `learner` | Tenant User | `password123` |

The health check is available at `http://127.0.0.1:8000/health/`.

After running `seed_demo`, log in as `tenantadmin` and open `http://127.0.0.1:8000/courses/` to see the sample course list. Tenant admins with an active tenant can create courses, lessons, assign tenant learners, and view progress. The seeded `learner` account is assigned to the sample course and can mark lessons complete.

## Demo workflow

1. Log in as `tenantadmin` and open **Courses**.
2. Create or edit a course, open its lessons, add/edit lessons, then open assignments and assign `learner`.
3. Log out and log in as `learner`; open **Courses**, open the assigned course lessons, and mark a lesson complete.
4. Log out and log in as `tenantadmin`; open the course progress page to see learner progress.
5. Log out and log in as `superadmin`; open **Tenants** to view/reactivate expired tenants.

The UI is intentionally plain. Backend tests enforce the permissions; hidden links are not relied on for security.

Trial expiration can be processed with:

```bash
.venv/bin/python manage.py expire_trials
```

The command is idempotent. Expired tenants keep their data but become read-only for tenant-scoped writes. Super Admins can reactivate tenants from the tenant list, starting a fresh 14-day trial.

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
