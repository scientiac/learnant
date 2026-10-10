# Learnant

<p align="center">
  <img src="core/static/core/learnant-ant.svg" width="88" alt="Learnant ant emblem">
</p>

Learnant is a secure learning workspace where each institute manages its own courses, lessons, and learners.

**Deployed site:** [learnant.3o14.com](https://learnant.3o14.com)

## Deploy

### Railway with GHCR

1. Create a Railway PostgreSQL service and a Django app service.
2. In Railway, configure the app service to pull `ghcr.io/<github-owner>/<repository>:master`. If the GHCR package is private, configure registry credentials in Railway.
3. Add the app's `DATABASE_URL` variable as a Railway reference to the PostgreSQL service, for example `${{Postgres.DATABASE_URL}}` (use your actual service name).
4. Set `SECRET_KEY` to a unique secret, set `DEBUG=false`, and set `ALLOWED_HOSTS` if you use hosts other than the Railway-provided domain or `learnant.3o14.com`. `RAILWAY_PUBLIC_DOMAIN` is automatically added to host and CSRF validation.
5. Attach a Railway volume to the app service at **`/app/uploads`** and set `MEDIA_ROOT=/app/uploads`. This preserves uploaded lesson media, avatars, and organization logos across app redeploys. Keep the volume; deleting it deletes uploaded files. Set this up before relying on media persistence.
6. Push to `master`. GitHub Actions builds and publishes the `:master` GHCR image and signs its digest. After the workflow succeeds, manually redeploy the Railway app to pull the updated image.
7. Set `LEARNANT_SUPERADMIN_USERNAME`, `LEARNANT_SUPERADMIN_EMAIL`, and `LEARNANT_SUPERADMIN_PASSWORD` as Railway app variables. Redeploy/restart the app service to apply them, then open its shell and run:

   ```bash
   python manage.py bootstrap_superadmin
   ```

   This command creates the initial platform Super Admin; setting the variables alone does not. The account must change its password on first login. If the command reports that the account already exists, it does not reset its password.

### Docker Compose

1. Copy `.env.example` to `.env` and set unique `SECRET_KEY` and `POSTGRES_PASSWORD` values.
2. Build and start the Django and PostgreSQL services:

   ```bash
   docker compose up --build -d
   ```

3. Open `http://localhost:8000/`. Migrations and static collection run at startup. PostgreSQL data and uploaded media use persistent Compose volumes.
4. To provision the first platform Super Admin, set the three `LEARNANT_SUPERADMIN_*` variables in `.env`, recreate the web service with `docker compose up -d web`, then run:

   ```bash
   docker compose exec web python manage.py bootstrap_superadmin
   ```

## Local development

1. Create and activate a virtual environment, then install dependencies:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Apply migrations and, optionally, seed local-only demo data:

   ```bash
   python manage.py migrate
   python manage.py seed_demo  # Optional; do not use for production data
   ```

3. Start Django and open `http://127.0.0.1:8000/`:

   ```bash
   python manage.py runserver
   ```

## Tests and checks

Run the automated test suite and Django checks from the repository root:

```bash
.venv/bin/python manage.py test
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
```
