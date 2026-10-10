# Multi-Tenant Learning Platform

A secure, minimal, multi-tenant learning platform for institutes and organizations built with Django and Django REST Framework.

---

## 1. Features & Highlights

- **Multi-Tenancy & Data Isolation:** Strict server-side scoping where tenant context is derived exclusively from authenticated user sessions. Cross-tenant ID manipulation is prevented via database constraints and 404/403 protections.
- **5-Tier Role-Based Access Control (RBAC):**
  - **Super Admin:** Platform control plus tenant-admin course, lesson, assignment, enrollment, and organization operations across active tenants; exclusive tenant reactivation.
  - **Admin:** The same tenant learning operations across active tenants, but no Super Admin grants, tenant deletion, or trial reactivation.
  - **Super Viewer:** Read-only platform-wide overview.
- **Tenant Admin:** Manages courses, ordered lessons, assignments, and learner progress for their institute.
  - **Tenant User:** Learner accessing assigned courses, completing lessons, and tracking progress.
- **Trial Lifecycle & Expiration:** 14-day default free trial with request-time boundary checks, idempotent scheduled expiration command (`python manage.py expire_trials`), read-only preservation of tenant data upon expiry, and Super Admin reactivation.
- **Subscription Administration:** Super Admins can switch an organization between trial and subscribed access, set an exact trial end, or adjust it by signed minutes, hours, days, or months.
- **Organization & Profile Branding:** Tenant Admins can manage institute contact details and upload a logo; users can upload a profile avatar. Uploaded images are served through access-controlled routes.
- **Modern UI:** shadcn/ui-inspired responsive interface built with Django templates, Tailwind CSS, and Inter typography.
- **Self-Service Onboarding:** Atomic tenant registration at `/signup/` creating an institute and Tenant Admin user in a single transaction.
- **Organization & Profile Settings:** Active Tenant Admins can update their own organization name/brand color; signed-in users can update their own display name and email.
- **Account Security:** Every signed-in role can change its password from Profile settings; the current password and Django password policy are checked.
- **Searchable Directories:** Search courses, lessons, colony members, assignments, progress, colonies, and a platform-wide Tenant Admin/learner directory. Platform results remain role-gated, and tenant-scoped results stay within the selected organization.
- **Bulk Student Onboarding:** Tenant Admins can create up to 100 tenant-bound learner accounts in one submission.
- **Spreadsheet Enrollment:** Tenant Admins can download a CSV template and import up to 500 learners with row-level validation, duplicate skipping, and optional same-tenant course assignments.
- **Temporary Learner Credentials:** Bulk-enrolled learners must replace their generated initial password before using the platform; seeded demo accounts remain ready to use.
- **Platform Account Security:** Deployment bootstrap provisions the first Super Admin from environment credentials; Super Admin-provisioned Admin/Super Viewer accounts receive one-time passwords and must reset them at first login.
- **Focused Lesson Study:** Assigned learners get a dedicated lesson page with syllabus navigation, sanitized GFM Markdown, KaTeX math, and protected inline image/video uploads inserted into lesson content.

---

## 2. Quickstart & Local Setup

### Run with Docker Compose (Django + PostgreSQL)

The supported container deployment runs Django and PostgreSQL as separate services, with named persistent volumes for the database and uploaded media:

```bash
cp .env.example .env
# Edit .env and set strong, unique SECRET_KEY and POSTGRES_PASSWORD values.
docker compose up --build -d
```

Open `http://localhost:8000/`. Migrations and static collection run when the web container starts. To seed demo data, run `docker compose exec web python manage.py seed_demo`. Create the first production Super Admin using the bootstrap environment credentials and `docker compose exec web python manage.py bootstrap_superadmin`.

The container image is published to `ghcr.io/<owner>/<repository>` on pushes to `main`/`master` and version tags. Branch tags such as `:master` are mutable and suitable for CI-triggered Railway redeploys. Pull requests build (but do not publish) the image. Published image digests are automatically signed using keyless Cosign; verify with `cosign verify` and the workflow identity shown in the GitHub Actions run. Use a tag or immutable digest when deploying elsewhere. Configure TLS/reverse proxying and persistent volumes for `/app/uploads` and PostgreSQL on your host.

### Run Django directly (development only)

```bash
# 1. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Or use .venv/bin/python directly

# 2. Install dependencies
pip install -r requirements.txt

# 3. Apply database migrations
python manage.py migrate

# 4. Seed demo data (creates tenants, courses, lessons, and users)
python manage.py seed_demo

# 5. Start development server
python manage.py runserver
```

Open `http://127.0.0.1:8000/` in your browser.

---

## 3. Demo Credentials

These credentials are for local development only, after running `python manage.py seed_demo`. They are not created or available in production.

| Username | Role | Scope | Key Capabilities |
|---|---|---|---|
| `superadmin` | Super Admin | Platform | Manage active tenant learning data; reactivate expired trials. |
| `admin` | Admin | Platform | Manage active tenant learning data; cannot reactivate trials. |
| `viewer` | Super Viewer | Platform | Read-only visibility across platform data. |
| `tenant_admin` | Tenant Admin | Demo Institute | Create/edit courses & lessons, enroll learners, view progress. |
| `institute_admin` | Tenant Admin (compatibility login) | Demo Institute | Same demo role and scope as `tenant_admin`. |
| `learner` | Tenant User | Tenant | View assigned courses, read lessons, mark completion. |

The system health check is available at `http://127.0.0.1:8000/health/`.

### Deployment Super Admin bootstrap

Set `LEARNANT_SUPERADMIN_USERNAME`, `LEARNANT_SUPERADMIN_EMAIL`, and `LEARNANT_SUPERADMIN_PASSWORD` in the deployment secret environment, then run `.venv/bin/python manage.py bootstrap_superadmin` after migrations. The command is idempotent, never prints the password, and creates an account that must change its password before proceeding. Do not put real values in `.env.example` or source control.

---

## 4. Demo Workflows

### Workflow 0: Bootstrap the deployment Super Admin
After applying migrations, provide the bootstrap credentials through your deployment's secret environment variables and run once:

```bash
python manage.py bootstrap_superadmin
```

The new Super Admin must change the temporary password on first login. The command is idempotent and does not print passwords. Do not commit real credentials.

### Workflow A: Self-Signup as a New Institute
1. Navigate to `http://127.0.0.1:8000/signup/`.
2. Fill in Organisation Name, Admin Username, Email, and Password.
3. Upon submission, the organization is created on an active 14-day trial, the user is created as Tenant Admin, and logged into the dashboard immediately.

### Workflow B: Managing Courses & Assignments (Tenant Admin)
1. Log in as `tenant_admin` (or `institute_admin`).
2. Visit **Courses** (`/courses/`).
3. Click **New course** to create a course.
4. Click **Lessons** to add or edit ordered lessons.
5. Click **Assignments** to assign the course to tenant learners (e.g., `learner`).
6. Click **Progress** to review lesson completion status across enrolled learners.

### Workflow C: Learner Study & Progress
1. Log in as `learner`.
2. Visit **Courses** (`/courses/`) to see assigned courses.
3. Open a course's lessons and click **Mark Complete**.
4. Progress status updates immediately with completion timestamps.

### Workflow D: Tenant Expiration & Super Admin Reactivation
1. Run trial expiration:
   ```bash
   python manage.py expire_trials
   ```
2. For an expired tenant, tenant users and admins retain read-only access to existing data; creation and updates are blocked with friendly notices.
3. Log in as `superadmin` and navigate to **Tenants** (`/tenants/`).
4. Use **Subscription** to switch Trial/Subscribed or adjust an exact trial end. Click **Reactivate** next to an expired tenant to start a fresh 14-day trial.

### Workflow G: Platform Tenant Administration
1. Log in as `admin` or `superadmin` and open **Tenants**.
2. Create a tenant with its initial Tenant Admin, or select **Courses**, **Members**, **Organization**, or **Enroll** on an active institute to administer its workspace.
3. Super Admin can additionally reactivate expired institutes and provision Admin/Super Viewer platform accounts.
4. Provisioned platform accounts must replace their temporary password before accessing platform pages. Super Viewer can open tenant courses but has no management actions.
5. Platform users can search all colony members and see Tenant Admin/owner accounts in the colony directory; Super Viewer access is read-only.

Tenant Admins can edit learner names, emails, and active status from **Members**. Deactivation preserves assignments and progress records.

### Workflow E: Organization & Profile Settings
1. As an active `tenant_admin`, use **Organization** to update the institute name, brand color, contact details, and logo.
2. Any signed-in user can open **Profile** to update their own first name, last name, email, avatar, and password. Role and tenant membership are not editable there.

### Workflow F: Bulk Student Onboarding
1. Log in as `tenant_admin` (or `institute_admin`) and open **Enroll students** (`/students/bulk-add/`).
2. Enter up to 100 usernames or email addresses, one per line.
3. Newly created learner usernames and randomly generated initial passwords are shown once after submission; share them with learners securely.

For CSV enrollment, download the tenant-specific template from the same page. Its comment lines map course IDs to titles. Fill `username`, `email`, `first_name`, and `last_name`; leave `course_ids` blank for no assignments or enter one or more same-tenant IDs separated by semicolons. The manual rows form offers the same fields and multi-course selection.

Tenant Admins can manage learner names, emails, and active status from **Members**. Deactivation preserves assignments and progress records.

---

## 5. Testing & Verification

The Tenant Admin dashboard includes an **AI Course Assistant Preview**. It accepts learner planning inputs and renders a static sample outline only; it does not call an AI service or create/persist a course. The `docs/ai-course-design.md` document remains for the developer to write.

Run the full automated test suite (207 tests):

```bash
python manage.py test
python manage.py check
```

Test suite coverage highlights:
- `test_permissions.py`: Role matrix enforcement across all 5 roles.
- `test_phase_auth_isolation.py`: Cross-tenant boundary enforcement and ID manipulation attacks.
- `test_courses.py` & `test_lessons.py`: Scoped CRUD operations and ordering constraints.
- `test_assignments.py`: Single-tenant validation between learners and courses.
- `test_progress.py`: Learner-isolated progress updates and unassigned course access prevention.
- `test_trials.py`: Trial start/end boundaries, idempotent expiration command, and Super Admin reactivation.
- `test_web.py`: Web views, redirects, and self-signup flows.

---

## 6. Architecture & Design Documentation

Detailed documentation is available in the `docs/` directory:
- [Architecture & System Design](architecture.md): Multi-tenancy approach, data isolation rules, RBAC, trial lifecycle, and data models.
- [Permissions Matrix](permissions.md): Complete policy breakdown for platform and tenant roles.
- [AI Course Creation Design](ai-course-design.md): Dedicated technical design document placeholder for human author completion.

---

## 7. Configuration & Database

- **Database:** Deployments use PostgreSQL. Docker Compose starts PostgreSQL and Django together; direct local development without a database URL uses a local SQLite database only for convenience. Set `DATABASE_URL` or the `POSTGRES_*` variables for direct PostgreSQL use.
- **Environment Variables:** Configure `DATABASE_URL`, `SECRET_KEY`, `DEBUG`, comma-separated `ALLOWED_HOSTS`, and `CSRF_TRUSTED_ORIGINS`. `learnant.3o14.com` is always allowed; when Railway provides `RAILWAY_PUBLIC_DOMAIN`, the app also adds that exact hostname and its HTTPS origin. Other hosts must be listed in the environment. Django does not auto-load `.env`.
- Production requires a strong `SECRET_KEY`, database URL, and host list. SMTP defaults to the standard backend when `DEBUG=false`; configure `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, and `EMAIL_USE_TLS` if the app begins sending email.
- **Static Files:** WhiteNoise serves collected assets from the container. The startup script applies migrations and runs `collectstatic` before starting Gunicorn.
- **Uploaded Media:** User/organization images and lesson media are stored as files under `MEDIA_ROOT` (default `/app/uploads` in the container). Mount a persistent volume at `/app/uploads` to retain them across container replacements; PostgreSQL stores their metadata and references.

### Portable container deployment

`Dockerfile`, `docker-compose.yml`, and `.github/workflows/publish-container.yml` provide a host-independent Django + PostgreSQL deployment and GHCR publishing. Configure `SECRET_KEY`, database credentials, `ALLOWED_HOSTS`, and `CSRF_TRUSTED_ORIGINS` on the target host. The application image does not bundle a database; deploy it alongside PostgreSQL and persist the PostgreSQL data directory and the media volume mounted at `/app/uploads`. Startup prepares the mounted directory for the non-root Django process. Gunicorn's optional control socket is disabled in the container because the service account has no login home and the HTTP app does not need the administrative socket. The workflow signs pushed image digests with keyless Cosign, so signatures are verifiable without distributing a private signing key.

### Step-by-step Railway deployment

1. **Publish the app image.** Push to `master` (or a version tag) and wait for the GitHub Actions **Build and publish container** workflow to complete. It publishes `ghcr.io/<github-owner>/<repository>:master` for the `master` branch (and `:latest` for the default branch) and signs the image digest with Cosign.
2. **Create PostgreSQL.** In Railway, create a PostgreSQL service in your project. Keep this service and its volume when redeploying the app; database contents do not live in the Django container.
3. **Deploy the image.** Add an app service using `ghcr.io/<github-owner>/<repository>:master`. If the package is private, configure Railway with permission to pull it. Expose port `8000` (or configure the service's target port as `8000`). Keep Railway's image source pointed at this mutable branch tag. After GitHub Actions publishes a new image, manually redeploy the Railway service to pull it; no Railway API token is needed.
4. **Link the database.** In the app service's Variables, set `DATABASE_URL` to a Railway reference to the Postgres service, such as `${{Postgres.DATABASE_URL}}` (replace `Postgres` with your service's exact name). Do not copy a URL for a different database or environment.
5. **Set app configuration.** Add `SECRET_KEY` as a strong, private random value; set `DEBUG=false`. `learnant.3o14.com` is already allowed. Railway's `RAILWAY_PUBLIC_DOMAIN` is also added automatically to `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`. If using another custom domain or host, add it to `ALLOWED_HOSTS` and its full HTTPS origin to `CSRF_TRUSTED_ORIGINS`.

   Generate a secret locally with `python -c "import secrets; print(secrets.token_urlsafe(50))"`, then paste the output into Railway's `SECRET_KEY` variable. Do not commit it or share it. The app deliberately refuses to start on Railway if its secret or PostgreSQL configuration is missing; it will not silently use SQLite.

6. **Deploy and check startup logs.** The container applies migrations and collects static files before starting Gunicorn. Confirm migrations complete and the service becomes healthy.
7. **Configure first Super Admin credentials.** In the app service's Variables, set `LEARNANT_SUPERADMIN_USERNAME`, `LEARNANT_SUPERADMIN_EMAIL`, and `LEARNANT_SUPERADMIN_PASSWORD`. Use a unique, strong password. Apply the variables/redeploy so they are available to the app's shell.
8. **Create the account once.** Open the app service's shell and run:

   ```bash
   python manage.py bootstrap_superadmin
   ```

   A successful first run prints `Provisioned bootstrap Super Admin: <username>` (never the password). Sign in with that username and the configured password; the account is required to change its password at first login. Setting these variables alone does not create the user: the command must be run explicitly against the app's configured database.

9. **Persist uploaded files.** In the Railway app service, open **Settings → Volumes → Add Volume** and use `/app/uploads` as the mount path. Add the service variable `MEDIA_ROOT=/app/uploads`. Lesson images/videos, avatars, and organization logos are files in this volume; PostgreSQL stores their metadata and references. The container prepares the mounted directory for its non-root Django user. Keep the volume when redeploying—deleting it deletes the media. Docker Compose also mounts a named `uploads` volume at `/app/uploads`. A new volume does not automatically copy files from the old container's temporary filesystem; copy any media that still exists before replacing that instance.
10. **Verify PostgreSQL and data.** In the same app shell, check the active database and tenant count:

   ```bash
   python manage.py shell -c "from django.conf import settings; from django.db import connection; from core.models import Tenant; print('engine:', settings.DATABASES['default']['ENGINE']); print('database:', connection.settings_dict['NAME']); print('host:', connection.settings_dict['HOST']); print('tenants:', Tenant.objects.count())"
   ```

   The engine must be `django.db.backends.postgresql`. If it reports SQLite, stop and fix the database variables before using the app. New PostgreSQL databases start empty; data previously stored only in a disposable container's SQLite file is not automatically copied over. If `bootstrap_superadmin` says the user already exists, it does not reset that user's password.

Once a lesson has been created, use **Add image or video** in its editor to upload one file at a time. Each upload is stored immediately on the persistent volume and its Markdown reference is inserted into the content field; save the lesson to retain other unsaved edits. You can keep adding more files, including multiple videos.

When publishing a new version, wait for the GHCR workflow and redeploy the app image. Do not delete or replace the PostgreSQL service/volume unless you intend to discard its data.

---

## 8. Time & Self-Deadline

- **Estimated Time:** 16 hours
- **Actual Time Taken:** ~12 hours (developer-recorded estimate)
- **Self-Deadline:** The original date/time was not recorded in the repository and cannot be reconstructed retrospectively; submitter should add it if known.
