# Checkpoint.md — Current Project State

> This file is the short handoff note between coding sessions.
> Update it after each verified task. Keep it factual and concise.
> Do not mark work complete based only on generated code; verify it.

## 1. Current Status

- **Overall status:** Course assignment flow verified with same-tenant validation and learner assigned-course access
- **Current phase:** Phase 4 — Courses, Lessons, and Assignments
- **Last verified commit:** 185636c Add course assignments
- **Last verified test run:** `.venv/bin/python manage.py test` — passed, 53 tests
- **Application starts locally:** Verified with runserver smoke check for `/health/`, anonymous assignment-list redirect, and anonymous assignment-create redirect
- **Database/migrations:** `.venv/bin/python manage.py migrate` — applied successfully with local SQLite
- **Next task:** Add lesson progress model and learner progress update flow with ownership validation.

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

**Task:** Course assignment model and tenant-admin assignment flow with same-tenant validation.

Expected actions:
- Add CourseAssignment model.
- Validate assigned course and learner belong to the same tenant.
- Allow Tenant Admin to assign own tenant learners to own tenant courses.
- Block assignments for expired/read-only tenants.
- Let learners see assigned courses and lessons.
- Run migrations, checks, tests, demo seed, and runserver smoke check.

**Acceptance criteria:**
- CourseAssignment model is migrated with duplicate prevention.
- Tenant Admin can assign only same-tenant learners to own tenant courses.
- Cross-tenant learner/course assignment attempts fail.
- Expired Tenant Admin cannot assign courses.
- Assigned learners can see assigned courses and lessons.
- Unassigned learners cannot access course lessons by ID.
- Tests and runserver smoke check pass.

## 7. Last Completed Task

- **Task:** Added CourseAssignment model, assignment list/create views, demo assignment seeding, and learner assigned-course access.
- **Files changed:** `core/models.py`, `core/forms.py`, `core/admin.py`, `core/views.py`, `config/urls.py`, `core/migrations/0005_courseassignment.py`, `core/templates/core/course_list.html`, `core/templates/core/assignment_list.html`, `core/templates/core/assignment_form.html`, `core/management/commands/seed_demo.py`, `core/test_assignments.py`, `README.md`, `CHECKPOINTS.md`.
- **Tests run:** `.venv/bin/python manage.py makemigrations core`; `.venv/bin/python manage.py migrate`; `.venv/bin/python manage.py check`; `.venv/bin/python manage.py test`; `.venv/bin/python manage.py seed_demo`; runserver assignment smoke script; `git diff --check`.
- **Test results:** Migration created and applied; check passed with 0 issues; 53 tests passed; demo data seeded locally; runserver assignment smoke passed; whitespace diff check passed.
- **Commit:** 185636c Add course assignments.

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
- **Task completed:** Added CourseAssignment model and tenant-admin assignment flow with same-tenant validation.
- **Files changed:** `core/models.py`, `core/forms.py`, `core/admin.py`, `core/views.py`, `config/urls.py`, `core/migrations/0005_courseassignment.py`, `core/templates/core/course_list.html`, `core/templates/core/assignment_list.html`, `core/templates/core/assignment_form.html`, `core/management/commands/seed_demo.py`, `core/test_assignments.py`, `README.md`, `CHECKPOINTS.md`.
- **Tests executed:** `.venv/bin/python manage.py makemigrations core`; `.venv/bin/python manage.py migrate`; `.venv/bin/python manage.py check`; `.venv/bin/python manage.py test`; `.venv/bin/python manage.py seed_demo`; runserver assignment smoke script; `git diff --check`.
- **Actual results:** Migration created and applied; check passed with 0 issues; 53 tests passed; demo data seeded locally; runserver assignment smoke passed; whitespace diff check passed.
- **Commit:** 185636c Add course assignments.
- **Current phase:** Phase 4 — Courses, Lessons, and Assignments.
- **Remaining issues:** PostgreSQL unavailable in PATH; reactivation duration policy still undecided; progress flow not implemented yet.
- **Next single task:** Add lesson progress model and learner progress update flow with ownership validation.
