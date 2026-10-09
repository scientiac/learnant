# Checkpoint.md — Current Project State

> This file is the short handoff note between coding sessions.
> Update it after each verified task. Keep it factual and concise.
> Do not mark work complete based only on generated code; verify it.

## 1. Current Status

- **Overall status:** Tenant-scoped course list verified locally with Tailwind/HTMX UI baseline
- **Current phase:** Phase 4 — Courses, Lessons, and Assignments
- **Last verified commit:** 918abd0 Add course list and Tailwind HTMX UI
- **Last verified test run:** `.venv/bin/python manage.py test` — passed, 28 tests
- **Application starts locally:** Verified with runserver smoke check for `/health/`, `/login/`, anonymous dashboard redirect, and anonymous course-list redirect
- **Database/migrations:** `.venv/bin/python manage.py migrate` — applied successfully with local SQLite
- **Next task:** Add tenant-admin course creation form with active-trial write enforcement and cross-tenant tests.

## 2. Project Decisions

- **Purpose:** Multi-tenant learning platform for institutes.
- **Backend:** Django.
- **API:** Django REST Framework where useful.
- **Database:** PostgreSQL for the completed application.
- **UI:** Django templates with Tailwind CSS and HTMX via CDN for a clean minimal interface; Django Admin for appropriately restricted internal administration.
- **Authentication:** Django authentication with a custom user model defined before the first migrations.
- **Tenant approach:** Shared database with tenant ownership on tenant-owned records; backend queries and permissions enforce isolation.
- **Trial:** Suggested 14-day trial, with request-time enforcement and an idempotent scheduled management command.
- **AI course creation:** Design/documentation only. The developer must write the AI design section themselves.
- **AI coding tools:** Prefer local Ollama plus Aider if compatible with available hardware. The app must not depend on these tools at runtime.
- **Payments/subscriptions:** Out of scope.
- **Priority order:** Tenant isolation, authorization, backend correctness, trial lifecycle, testing, then UI polish.

If any decision conflicts with the original take-home specification or existing project constraints, stop and ask the developer before changing direction.

## 3. Roles

- **Super Admin:** Full platform-level administration, including tenant creation, management, and reactivation.
- **Admin:** Limited platform-level administration; exact permissions must be documented.
- **Super Viewer:** Platform-level read-only access to explicitly permitted information.
- **Tenant Admin:** Manages users, courses, lessons, assignments, and progress inside their own tenant.
- **Tenant User:** Accesses assigned courses/lessons and updates their own progress.

Do not assume the UI protects any of these actions. Enforce authorization on the backend.

## 4. Security Invariants

These rules must remain true throughout implementation:

1. Tenant identity comes from trusted server-side user context, not an untrusted request field.
2. Tenant-owned list and detail queries are scoped to the authorized tenant.
3. All create/update/delete/assignment/progress operations validate authorization.
4. Related records must belong to the same tenant where required.
5. Learners can access only their assigned courses and their own progress.
6. Users cannot promote themselves, change their tenant, or gain platform privileges through request data.
7. Trial expiry is checked during restricted requests; a scheduled command is not the only enforcement.
8. Expiration preserves existing user and learning data.
9. Security bugs get regression tests.
10. Never claim a test passed unless the test was run and passed.

## 5. Phase Tracker

Mark an item complete only after its acceptance criteria and relevant tests have been verified.

- [x] Phase 0 — Repository and project setup
- [x] Phase 1 — Tenant and user foundations
- [ ] Phase 2 — Authentication and authorization
- [ ] Phase 3 — Tenant isolation
- [ ] Phase 4 — Courses, lessons, and assignments
- [ ] Phase 5 — Learning progress
- [ ] Phase 6 — Trial expiration and reactivation
- [ ] Phase 7 — Minimal usable UI
- [ ] Phase 8 — Verification and security review
- [ ] Phase 9 — Documentation and submission

## 6. Current Task

**Task:** Add Tailwind/HTMX UI baseline and tenant-scoped course list.

Expected actions:
- Update implementation plan to use Tailwind CSS and HTMX for the frontend UI baseline.
- Avoid adding package dependencies for UI tooling at this stage; use CDN links.
- Add the smallest Course model.
- Add protected course list scoped by role and tenant.
- Run migrations, checks, tests, demo seed, and runserver smoke check.

**Acceptance criteria:**
- Plan and docs mention Tailwind/HTMX UI approach.
- Course model is migrated.
- Tenant Admin sees only own tenant courses.
- Tenant User does not see unassigned courses yet.
- Super Viewer can read all courses.
- Tests and runserver smoke check pass.

## 7. Last Completed Task

- **Task:** Switched templates to Tailwind/HTMX CDN baseline and added tenant-scoped Course model/list page with isolation tests.
- **Files changed:** `PLANS.md`, `DOCUMENT.sh`, `README.md`, `config/urls.py`, `core/admin.py`, `core/models.py`, `core/views.py`, `core/migrations/0003_course.py`, `core/templates/`, `core/management/commands/seed_demo.py`, `core/test_courses.py`, `CHECKPOINTS.md`.
- **Tests run:** `.venv/bin/python manage.py makemigrations core`; `.venv/bin/python manage.py migrate`; `.venv/bin/python manage.py check`; `.venv/bin/python manage.py test`; `.venv/bin/python manage.py seed_demo`; runserver course web smoke script; `git diff --check`.
- **Test results:** Migration created and applied; check passed with 0 issues; 28 tests passed; demo data seeded locally; runserver course web smoke passed; whitespace diff check passed.
- **Commit:** 918abd0 Add course list and Tailwind HTMX UI.

Update this section after completing the first task.

## 8. Known Issues and Decisions Needed

- PostgreSQL client/server is not available in the current PATH; app is configured for PostgreSQL via env vars and SQLite fallback for local development.
- Super Viewer policy confirmed: platform-level read-only user.
- Admin policy confirmed at high level: platform-level administrative user with a defined subset of Super Admin permissions. Initial subset documented in `docs/permissions.md`.
- Expired tenant policy confirmed: existing authorized data remains viewable/read-only; no tenant-scoped user may add to or mutate the system after expiration.
- Decide the reactivation policy and document it.
- Git repository initialized locally; first commit not yet recorded.

Record only unresolved decisions here; remove items when resolved.

## 9. Handoff Format

At the end of each coding session, update this file using this compact format:

### Latest Update
- **Task completed:**
- **Files changed:**
- **Tests executed:**
- **Actual results:**
- **Commit:**
- **Current phase:**
- **Remaining issues:**
- **Next single task:**

Do not paste full source files, long logs, or the entire conversation into this checkpoint. Keep detailed reasoning in the relevant documentation or Git history and retain only the facts needed to resume efficiently.

### Latest Update
- **Task completed:** Added Tailwind/HTMX UI baseline and tenant-scoped course list.
- **Files changed:** `PLANS.md`, `DOCUMENT.sh`, `README.md`, `config/urls.py`, `core/admin.py`, `core/models.py`, `core/views.py`, `core/migrations/0003_course.py`, `core/templates/`, `core/management/commands/seed_demo.py`, `core/test_courses.py`, `CHECKPOINTS.md`.
- **Tests executed:** `.venv/bin/python manage.py makemigrations core`; `.venv/bin/python manage.py migrate`; `.venv/bin/python manage.py check`; `.venv/bin/python manage.py test`; `.venv/bin/python manage.py seed_demo`; runserver course web smoke script; `git diff --check`.
- **Actual results:** Migration created and applied; check passed with 0 issues; 28 tests passed; demo data seeded locally; runserver course web smoke passed; whitespace diff check passed.
- **Commit:** 918abd0 Add course list and Tailwind HTMX UI.
- **Current phase:** Phase 4 — Courses, Lessons, and Assignments.
- **Remaining issues:** PostgreSQL unavailable in PATH; reactivation duration policy still undecided; course creation/lesson/assignment/progress flows not implemented yet.
- **Next single task:** Add tenant-admin course creation form with active-trial write enforcement and cross-tenant tests.
