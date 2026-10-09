# Checkpoint.md — Current Project State

> This file is the short handoff note between coding sessions.
> Update it after each verified task. Keep it factual and concise.
> Do not mark work complete based only on generated code; verify it.

## 1. Current Status

- **Overall status:** Phase 7 minimal usable workflows verified
- **Current phase:** Phase 8 — Verification and security review
- **Last verified commit:** f55ef21 Add minimal demo workflow polish
- **Last verified test run:** `.venv/bin/python manage.py test` — passed, 86 tests
- **Application starts locally:** Verified with runserver smoke check for `/health/`, `/login/`, and protected workflow redirects
- **Database/migrations:** `.venv/bin/python manage.py migrate` — applied successfully with local SQLite
- **Next task:** Run Phase 8 verification/security review and add any regression tests for findings.

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
- [x] Phase 2 — Authentication and authorization
- [x] Phase 3 — Tenant isolation
- [x] Phase 4 — Courses, lessons, and assignments
- [x] Phase 5 — Learning progress
- [x] Phase 6 — Trial expiration and reactivation
- [x] Phase 7 — Minimal usable UI
- [ ] Phase 8 — Verification and security review
- [ ] Phase 9 — Documentation and submission

Notes:
- Phase 2 is checked because login/logout, protected pages, role helpers, documented permissions, role denials, and admin access restrictions are verified.
- Phase 3 is checked because tenant-owned list/detail/update/delete/assignment/progress paths are scoped and ID manipulation tests are verified.
- Phase 4 is checked because course/lesson list/create/update/delete basics, assignment create/revoke, same-tenant validation, expired-tenant write blocking, and regression tests are verified.
- Phase 5 is checked because learner progress ownership, tenant-admin progress visibility, expired-tenant read-only behavior, and progress tests are verified.
- Phase 6 is checked because request-time write blocking, idempotent expiration command, data preservation, and Super Admin-only reactivation are verified.
- Phase 7 is checked because main demo workflows have simple navigation/instructions, backend permissions remain enforced by tests, and smoke checks pass.

## 6. Current Task

**Task:** Verification and security review.

Expected actions:
- Run the complete test suite and Django checks.
- Review authentication, authorization, and every tenant-owned endpoint.
- Test cross-tenant ID manipulation, role escalation, assignment consistency, expiration boundaries, and repeated expiration processing.
- Fix findings and add regression tests.
- Review diff/status for unrelated changes.

**Acceptance criteria:**
- All tests pass or failures are documented accurately.
- No known critical tenant-isolation flaw remains.
- Changed code and permission decisions are understandable.

## 7. Last Completed Task

- **Task:** Added minimal role-aware navigation and README demo workflow guidance for browser demonstration.
- **Files changed:** `core/templates/base.html`, `core/templates/core/dashboard.html`, `core/test_web.py`, `README.md`, `CHECKPOINTS.md`.
- **Tests run:** `.venv/bin/python manage.py check`; `.venv/bin/python manage.py test`; `.venv/bin/python manage.py seed_demo`; runserver Phase 7 smoke script.
- **Test results:** Check passed with 0 issues; 86 tests passed; demo data seeded locally; runserver Phase 7 smoke passed.
- **Commit:** f55ef21 Add minimal demo workflow polish.

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
- **Task completed:** Added minimal usable workflow navigation and demo guidance.
- **Files changed:** `core/templates/base.html`, `core/templates/core/dashboard.html`, `core/test_web.py`, `README.md`, `CHECKPOINTS.md`.
- **Tests executed:** `.venv/bin/python manage.py check`; `.venv/bin/python manage.py test`; `.venv/bin/python manage.py seed_demo`; runserver Phase 7 smoke script.
- **Actual results:** Check passed with 0 issues; 86 tests passed; demo data seeded locally; runserver Phase 7 smoke passed.
- **Commit:** f55ef21 Add minimal demo workflow polish.
- **Current phase:** Phase 8 — Verification and security review.
- **Remaining issues:** PostgreSQL unavailable in PATH; Phase 8/9 remain.
- **Next single task:** Run Phase 8 verification/security review and add any regression tests for findings.
