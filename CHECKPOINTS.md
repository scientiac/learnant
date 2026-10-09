# Checkpoint.md — Current Project State

> This file is the short handoff note between coding sessions.
> Update it after each verified task. Keep it factual and concise.
> Do not mark work complete based only on generated code; verify it.

## 1. Current Status

- **Overall status:** Trial expiration command and Super Admin reactivation verified
- **Current phase:** Phase 4 — Courses, Lessons, and Assignments finalization
- **Last verified commit:** 897d9a8 Add trial expiration and reactivation
- **Last verified test run:** `.venv/bin/python manage.py test` — passed, 67 tests
- **Application starts locally:** Verified with runserver smoke check for `/health/` and anonymous tenant-list redirect
- **Database/migrations:** `.venv/bin/python manage.py migrate` — applied successfully with local SQLite
- **Next task:** Close remaining Phase 4 gaps: assignment revocation and minimal course/lesson update/delete permissions.

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
- [x] Phase 6 — Trial expiration and reactivation
- [ ] Phase 7 — Minimal usable UI
- [ ] Phase 8 — Verification and security review
- [ ] Phase 9 — Documentation and submission

Notes:
- Phase 2 is not checked yet because broader protected administrative operations still need review.
- Phase 3 is not checked yet because tenant isolation must be reviewed across every endpoint after progress/trial work is added.
- Phase 4 is not checked yet because course/lesson/assignment basics exist, but remaining update/delete/revocation and final acceptance review are not complete.
- Phase 5 is checked because learner progress ownership, tenant-admin progress visibility, expired-tenant read-only behavior, and progress tests are verified.
- Phase 6 is checked because request-time write blocking, idempotent expiration command, data preservation, and Super Admin-only reactivation are verified.

## 6. Current Task

**Task:** Close remaining Phase 4 course/lesson/assignment gaps.

Expected actions:
- Add assignment revocation for Tenant Admins in their own active tenant.
- Add minimal course/lesson update/delete where required by Phase 4.
- Enforce tenant scope and expired-tenant read-only behavior for each write.
- Add tests for cross-tenant ID manipulation and denied roles.
- Run checks, tests, demo seed, and smoke checks.

**Acceptance criteria:**
- Tenant Admin can update/delete only own-tenant courses/lessons while active.
- Tenant Admin can revoke only own-tenant assignments while active.
- Expired tenants cannot update/delete/revoke.
- Tenant User and Super Viewer cannot mutate tenant learning records.
- Tests and smoke checks pass.

## 7. Last Completed Task

- **Task:** Added `expired_at`, request-time trial write blocking, idempotent `expire_trials` command, tenant list, and Super Admin-only tenant reactivation.
- **Files changed:** `core/models.py`, `core/permissions.py`, `core/views.py`, `config/urls.py`, `core/migrations/0007_tenant_expired_at.py`, `core/management/commands/expire_trials.py`, `core/templates/core/dashboard.html`, `core/templates/core/tenant_list.html`, `core/test_trials.py`, `docs/permissions.md`, `README.md`, `CHECKPOINTS.md`.
- **Tests run:** `.venv/bin/python manage.py makemigrations core`; `.venv/bin/python manage.py migrate`; `.venv/bin/python manage.py check`; `.venv/bin/python manage.py test`; `.venv/bin/python manage.py seed_demo`; runserver trial smoke script; `git diff --check`.
- **Test results:** Migration created and applied; check passed with 0 issues; 67 tests passed; demo data seeded locally; runserver trial smoke passed; whitespace diff check passed.
- **Commit:** 897d9a8 Add trial expiration and reactivation.

Update this section after completing the first task.

## 8. Known Issues and Decisions Needed

- PostgreSQL client/server is not available in the current PATH; app is configured for PostgreSQL via env vars and SQLite fallback for local development.
- Super Viewer policy confirmed: platform-level read-only user.
- Admin policy confirmed at high level: platform-level administrative user with a defined subset of Super Admin permissions. Initial subset documented in `docs/permissions.md`.
- Expired tenant policy confirmed: existing authorized data remains viewable/read-only; no tenant-scoped user may add to or mutate the system after expiration.
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
- **Task completed:** Added idempotent trial expiration command and Super Admin reactivation.
- **Files changed:** `core/models.py`, `core/permissions.py`, `core/views.py`, `config/urls.py`, `core/migrations/0007_tenant_expired_at.py`, `core/management/commands/expire_trials.py`, `core/templates/core/dashboard.html`, `core/templates/core/tenant_list.html`, `core/test_trials.py`, `docs/permissions.md`, `README.md`, `CHECKPOINTS.md`.
- **Tests executed:** `.venv/bin/python manage.py makemigrations core`; `.venv/bin/python manage.py migrate`; `.venv/bin/python manage.py check`; `.venv/bin/python manage.py test`; `.venv/bin/python manage.py seed_demo`; runserver trial smoke script; `git diff --check`.
- **Actual results:** Migration created and applied; check passed with 0 issues; 67 tests passed; demo data seeded locally; runserver trial smoke passed; whitespace diff check passed.
- **Commit:** 897d9a8 Add trial expiration and reactivation.
- **Current phase:** Phase 4 — Courses, Lessons, and Assignments finalization.
- **Remaining issues:** PostgreSQL unavailable in PATH; Phase 4 update/delete/revocation acceptance still needs final pass; Phase 2/3 need final authorization/isolation review before ticking.
- **Next single task:** Add assignment revocation and minimal course/lesson update/delete permissions.
