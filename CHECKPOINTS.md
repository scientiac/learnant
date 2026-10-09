# Checkpoint.md — Current Project State

> This file is the short handoff note between coding sessions.
> Update it after each verified task. Keep it factual and concise.
> Do not mark work complete based only on generated code; verify it.

## 1. Current Status

- **Overall status:** Phase 4 course/lesson/assignment CRUD and revocation permissions verified
- **Current phase:** Phase 2/3 authorization and isolation final review
- **Last verified commit:** 897d9a8 Add trial expiration and reactivation
- **Last verified test run:** `.venv/bin/python manage.py test` — passed, 80 tests
- **Application starts locally:** Verified with runserver smoke check for `/health/` and anonymous tenant-list redirect
- **Database/migrations:** `.venv/bin/python manage.py migrate` — applied successfully with local SQLite
- **Next task:** Review Phase 2/3 acceptance criteria and add any missing authorization/isolation regression tests before ticking them.

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
- [x] Phase 4 — Courses, lessons, and assignments
- [x] Phase 5 — Learning progress
- [x] Phase 6 — Trial expiration and reactivation
- [ ] Phase 7 — Minimal usable UI
- [ ] Phase 8 — Verification and security review
- [ ] Phase 9 — Documentation and submission

Notes:
- Phase 2 is not checked yet because broader protected administrative operations still need review.
- Phase 3 is not checked yet because tenant isolation must be reviewed across every endpoint after progress/trial work is added.
- Phase 4 is checked because course/lesson list/create/update/delete basics, assignment create/revoke, same-tenant validation, expired-tenant write blocking, and regression tests are verified.
- Phase 5 is checked because learner progress ownership, tenant-admin progress visibility, expired-tenant read-only behavior, and progress tests are verified.
- Phase 6 is checked because request-time write blocking, idempotent expiration command, data preservation, and Super Admin-only reactivation are verified.

## 6. Current Task

**Task:** Phase 2/3 authorization and tenant-isolation final review.

Expected actions:
- Review protected views/endpoints for anonymous access, role restrictions, and server-side authorization.
- Review tenant-owned queries for tenant scoping and ID manipulation protection.
- Add any missing regression tests for Phase 2/3 acceptance criteria.
- Run checks, tests, demo seed, and smoke checks.

**Acceptance criteria:**
- Anonymous users cannot access protected functionality.
- Each role is allowed only documented operations.
- Tenant-owned list/detail/update/delete/assignment/progress queries are scoped to the authorized tenant.
- Cross-tenant ID manipulation is denied without leaking data to tenant users.
- Tests and smoke checks pass.

## 7. Last Completed Task

- **Task:** Added course update/delete, lesson update/delete, and assignment revocation with tenant/role/expiry checks.
- **Files changed:** `core/views.py`, `config/urls.py`, `core/templates/core/course_list.html`, `core/templates/core/lesson_list.html`, `core/templates/core/assignment_list.html`, `core/templates/core/confirm_delete.html`, `core/test_courses.py`, `core/test_lessons.py`, `core/test_assignments.py`, `CHECKPOINTS.md`.
- **Tests run:** `.venv/bin/python manage.py check`; `.venv/bin/python manage.py test`.
- **Test results:** Check passed with 0 issues; 80 tests passed.
- **Commit:** Pending.

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
- **Task completed:** Completed Phase 4 mutation/revocation permissions.
- **Files changed:** `core/views.py`, `config/urls.py`, `core/templates/core/course_list.html`, `core/templates/core/lesson_list.html`, `core/templates/core/assignment_list.html`, `core/templates/core/confirm_delete.html`, `core/test_courses.py`, `core/test_lessons.py`, `core/test_assignments.py`, `CHECKPOINTS.md`.
- **Tests executed:** `.venv/bin/python manage.py check`; `.venv/bin/python manage.py test`.
- **Actual results:** Check passed with 0 issues; 80 tests passed.
- **Commit:** Pending.
- **Current phase:** Phase 2/3 authorization and tenant-isolation final review.
- **Remaining issues:** PostgreSQL unavailable in PATH; Phase 2/3 need final authorization/isolation review before ticking.
- **Next single task:** Review Phase 2/3 acceptance criteria and add any missing authorization/isolation regression tests before ticking them.
