# Checkpoint.md — Current Project State

> This file is the short handoff note between coding sessions.
> Update it after each verified task. Keep it factual and concise.
> Do not mark work complete based only on generated code; verify it.

## 1. Current Status

- **Overall status:** Lesson progress flow verified with learner ownership checks and expired-tenant read-only enforcement
- **Current phase:** Phase 6 — Trial Expiration and Reactivation
- **Last verified commit:** fa08037 Clarify checkpoint phase tracking
- **Last verified test run:** `.venv/bin/python manage.py test` — passed, 61 tests
- **Application starts locally:** Verified with runserver smoke check for `/health/`, anonymous progress-list redirect, and anonymous lesson-list redirect
- **Database/migrations:** `.venv/bin/python manage.py migrate` — applied successfully with local SQLite
- **Next task:** Add idempotent trial-expiration command and request-time expiry enforcement/re-activation policy.

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
- [x] Phase 5 — Learning progress
- [ ] Phase 6 — Trial expiration and reactivation
- [ ] Phase 7 — Minimal usable UI
- [ ] Phase 8 — Verification and security review
- [ ] Phase 9 — Documentation and submission

Notes:
- Phase 2 is not checked yet because broader protected administrative operations still need review.
- Phase 3 is not checked yet because tenant isolation must be reviewed across every endpoint after progress/trial work is added.
- Phase 4 is not checked yet because course/lesson/assignment basics exist, but remaining update/delete/revocation and final acceptance review are not complete.
- Phase 5 is checked because learner progress ownership, tenant-admin progress visibility, expired-tenant read-only behavior, and progress tests are verified.

## 6. Current Task

**Task:** Trial expiration and reactivation foundation.

Expected actions:
- Enforce trial expiration during protected write requests.
- Add an idempotent management command to mark expired tenants.
- Add authorized Super Admin reactivation behavior.
- Preserve tenant data after expiration.
- Run checks, tests, demo seed, and smoke checks.

**Acceptance criteria:**
- Tenants expire at the configured boundary.
- Expiration command is idempotent and preserves data.
- Expired tenants are read-only for tenant-scoped writes.
- Only Super Admin can reactivate tenants.
- Tests and smoke checks pass.

## 7. Last Completed Task

- **Task:** Added LessonProgress model, learner mark-complete flow, and tenant-admin progress view with ownership/isolation tests.
- **Files changed:** `core/models.py`, `core/admin.py`, `core/views.py`, `config/urls.py`, `core/migrations/0006_lessonprogress.py`, `core/templates/core/course_list.html`, `core/templates/core/lesson_list.html`, `core/templates/core/progress_list.html`, `core/test_progress.py`, `README.md`, `CHECKPOINTS.md`.
- **Tests run:** `.venv/bin/python manage.py makemigrations core`; `.venv/bin/python manage.py migrate`; `.venv/bin/python manage.py check`; `.venv/bin/python manage.py test`; `.venv/bin/python manage.py seed_demo`; runserver progress smoke script; `git diff --check`.
- **Test results:** Migration created and applied; check passed with 0 issues; 61 tests passed; demo data seeded locally; runserver progress smoke passed; whitespace diff check passed.
- **Commit:** Pending.

Update this section after completing the first task.

## 8. Known Issues and Decisions Needed

- PostgreSQL client/server is not available in the current PATH; app is configured for PostgreSQL via env vars and SQLite fallback for local development.
- Super Viewer policy confirmed: platform-level read-only user.
- Admin policy confirmed at high level: platform-level administrative user with a defined subset of Super Admin permissions. Initial subset documented in `docs/permissions.md`.
- Expired tenant policy confirmed: existing authorized data remains viewable/read-only; no tenant-scoped user may add to or mutate the system after expiration.
- Decide the reactivation policy and document it.
- Git repository initialized locally with checkpoint commits recorded.

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
- **Task completed:** Added LessonProgress model and learner progress update flow with ownership validation.
- **Files changed:** `core/models.py`, `core/admin.py`, `core/views.py`, `config/urls.py`, `core/migrations/0006_lessonprogress.py`, `core/templates/core/course_list.html`, `core/templates/core/lesson_list.html`, `core/templates/core/progress_list.html`, `core/test_progress.py`, `README.md`, `CHECKPOINTS.md`.
- **Tests executed:** `.venv/bin/python manage.py makemigrations core`; `.venv/bin/python manage.py migrate`; `.venv/bin/python manage.py check`; `.venv/bin/python manage.py test`; `.venv/bin/python manage.py seed_demo`; runserver progress smoke script; `git diff --check`.
- **Actual results:** Migration created and applied; check passed with 0 issues; 61 tests passed; demo data seeded locally; runserver progress smoke passed; whitespace diff check passed.
- **Commit:** Pending.
- **Current phase:** Phase 6 — Trial Expiration and Reactivation.
- **Remaining issues:** PostgreSQL unavailable in PATH; reactivation duration policy still undecided; Phase 4 update/delete/revocation acceptance still needs final pass.
- **Next single task:** Add idempotent trial-expiration command and request-time expiry enforcement/reactivation policy.
