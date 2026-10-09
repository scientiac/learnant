# PLANS.md — Multi-Tenant Learning Platform

## 1. Project Goal

Build a small, secure, working multi-tenant learning platform for institutes.

The application must support platform administrators, tenant administrators, and learners. Each tenant must have isolated users, courses, assignments, and learning progress. Tenants receive a free trial and lose access to restricted learning features when the trial expires.

AI-powered course generation is **design/documentation only**. Do not implement AI generation or connect to a paid AI API.

## 2. Guiding Rules

- Prefer the simplest implementation that satisfies the task.
- Reuse Django features instead of building infrastructure from scratch.
- Use a modular Django application; do not introduce microservices.
- Keep the UI functional and simple. Security and correctness matter more than visual polish.
- Work on one phase or small task at a time.
- Inspect relevant existing files before changing code; do not reread the whole repository unnecessarily.
- Write tests with each feature, not only at the end.
- Never claim a test passed unless it was actually run and passed.
- Do not make unrelated changes during a task.
- Do not add dependencies without explaining why they are needed.
- Keep secrets out of source control.
- Make changes understandable enough for the developer to explain in an interview.
- The developer must write the `docs/ai-course-design.md` content themselves because the take-home task explicitly prohibits using AI to write that design/documentation.

## 3. Intended Stack

- Python and Django
- Django REST Framework where API endpoints are useful
- PostgreSQL for the completed application
- Django authentication and a custom user model
- Django templates with HTMX and Tailwind CSS for a clean, minimal interface
- Django Admin for internal administration, with appropriate access restrictions
- Django migrations for schema changes
- Django's test framework (and other test tools only if justified)
- Git for checkpoints and rollback
- Optional: Ollama plus Aider for local AI-assisted coding; the app must not depend on them at runtime

Do not introduce React, Celery, Redis, payment processing, multi-database tenancy, or actual AI course generation unless a requirement cannot reasonably be met without it and the developer approves the change.

## 4. Roles and Permission Decisions

Implement these five roles:

1. **Super Admin** — full platform-level administration, including tenant creation, management, and reactivation.
2. **Admin** — a documented subset of platform-level administrative permissions. Initial suggested policy: may create and view tenants and manage tenant accounts, but may not grant Super Admin privileges or perform destructive tenant deletion. Finalize the exact policy in the documentation.
3. **Super Viewer** — platform-wide read-only access to explicitly permitted platform information.
4. **Tenant Admin** — manages users, courses, lessons, assignments, and learning progress inside their own tenant.
5. **Tenant User** — accesses assigned courses and lessons and updates their own progress.

Additional decisions to document and enforce:
- Whether platform administrators can enter learner-facing course areas.
- Whether Tenant Admins can preview courses.
- Which information Super Viewer can see.
- Which limited operations remain available after trial expiry.

Enforce authorization on the backend. Hiding a button or page is not authorization.

## 5. Tenant Isolation Rules — Non-Negotiable

- Derive tenant identity from trusted, authenticated server-side data, not from a client-supplied tenant ID.
- Scope every tenant-owned list and detail query to the authorized tenant.
- Apply checks to reads, creates, updates, deletes, assignments, and progress operations.
- Validate tenant consistency across related records (for example, assigned learner and course must belong to the same tenant).
- A Tenant Admin cannot access another tenant's users, courses, lessons, assignments, or progress.
- A Tenant User can access only courses assigned to them and progress belonging to them.
- A user cannot self-assign a role, change their tenant, or gain platform privileges through request data.
- Validate object access even when a requester manually changes a URL or API object ID.
- Add regression tests for every discovered isolation flaw.
- Do not rely on frontend filtering or a scheduled task for security.
- Use consistent authorization helpers/permission classes rather than duplicating ad hoc checks everywhere.

## 6. Suggested Data Model

Start with the smallest useful set of models and expand only when required.

- **Tenant**: name, status, trial start/end timestamps, expiration metadata, creation timestamps.
- **User**: Django authentication fields plus role and tenant association where appropriate. Configure the custom user model before the first project migration.
- **Course**: tenant, title, description, creator, timestamps.
- **Lesson**: course, title, content, order.
- **CourseAssignment**: tenant, course, learner, assigned timestamp.
- **LessonProgress**: assignment, lesson, completion status/timestamp.

Model constraints and validation should prevent invalid relationships and duplicate assignments/progress. Keep platform-level users' tenant association nullable only if the design requires it, and enforce role/tenant consistency.

## 7. Tenant Trial Lifecycle

- Suggested default trial length: 14 days; make it a clear configuration or documented policy.
- Record exact server-side trial start and end timestamps.
- Define expiry as `current_time >= trial_ends_at`.
- Check expiry during each restricted learning operation; a scheduled job alone is insufficient.
- Add an idempotent Django management command that marks eligible tenants expired.
- Running the expiration command repeatedly must not create duplicate side effects or damage data.
- Keep tenant users and learning data when a tenant expires.
- Restrict learning operations according to the documented policy.
- Permit reactivation only through an authorized platform-level operation.
- Document whether reactivation starts a new trial or sets an active status/end date.
- Test boundary times, repeated processing, and reactivation.

Do not implement payments or subscriptions.

## 8. Implementation Phases

Complete phases in order. Do not begin the next phase until the current phase's acceptance criteria and tests pass, unless a documented dependency requires a change.

### Phase 0 — Repository and Project Setup

Tasks:
- Inspect the repository and existing instructions before changing anything.
- Record the agreed stack and local run commands.
- Create or verify the Django project and app structure.
- Set up environment-variable configuration and a safe `.env.example`.
- Configure PostgreSQL for the completed application; SQLite may be used only for a temporary initial smoke test if useful.
- Add `.gitignore`, dependency specification, and initial migrations.
- Configure the custom user model before the first migrations.
- Add a basic health/smoke check and verify the app starts.

Acceptance criteria:
- A clean local setup can install dependencies and start the application.
- Migrations run successfully.
- No secrets are committed.
- Setup instructions are documented.
- Initial tests pass.

### Phase 1 — Tenant and User Foundations

Tasks:
- Implement Tenant and the custom User model.
- Add role choices and tenant membership rules.
- Add basic tenant/user creation through a controlled administrative path.
- Configure Django Admin safely.
- Add model validation and database constraints where appropriate.

Acceptance criteria:
- All five roles can be represented.
- Platform users and tenant users have unambiguous tenant semantics.
- Invalid role/tenant combinations are rejected.
- Model tests pass.

### Phase 2 — Authentication and Authorization

Tasks:
- Implement login/logout or the required authentication endpoints.
- Implement reusable role and tenant permission checks.
- Document the permission matrix.
- Ensure users cannot modify their own role or tenant through normal requests.
- Protect administrative operations on the backend.

Acceptance criteria:
- Anonymous users cannot access protected functionality.
- Each role is allowed only its documented operations.
- Permission tests cover allowed and denied cases.
- UI visibility is not the only access control.

### Phase 3 — Tenant Isolation

Tasks:
- Scope tenant-owned list and detail queries.
- Validate tenant ownership when creating or modifying records.
- Validate related-object consistency.
- Protect Django Admin paths and querysets against cross-tenant access where tenant users can use them.
- Test ID manipulation and direct endpoint access.

Acceptance criteria:
- Tenant A cannot read or modify Tenant B's users or records.
- Tenant Admins cannot manage another tenant's resources.
- Learners cannot access unassigned courses or other learners' progress.
- Client-supplied tenant IDs cannot override trusted tenant context.
- Cross-tenant regression tests pass.

### Phase 4 — Courses, Lessons, and Assignments

Tasks:
- Implement course CRUD within the authorized tenant.
- Implement lesson CRUD and ordering.
- Implement course assignment and removal/revocation if required.
- Prevent duplicate assignments.
- Validate that course and learner belong to the same tenant.

Acceptance criteria:
- Tenant Admins can manage only their own tenant's courses, lessons, and users.
- Learners can list only their assigned courses.
- Cross-tenant assignment attempts are rejected.
- CRUD and assignment tests pass.

### Phase 5 — Learning Progress

Tasks:
- Let learners read assigned course and lesson content.
- Let learners mark lessons complete or update progress.
- Let learners see their own progress.
- Let Tenant Admins view progress for learners in their own tenant.
- Prevent duplicate or inconsistent progress records.

Acceptance criteria:
- Progress is saved against the correct assignment and lesson.
- Learners cannot read or modify another learner's progress.
- Tenant Admins cannot view another tenant's progress.
- Progress tests pass.

### Phase 6 — Trial Expiration and Reactivation

Tasks:
- Implement trial timestamps and lifecycle status.
- Enforce expiry on restricted learning operations at request time.
- Add an idempotent expiration management command.
- Add authorized reactivation.
- Document what expired users can and cannot do.

Acceptance criteria:
- New tenants receive the configured trial period.
- Access is denied at and after the trial end time.
- Existing data is preserved.
- Re-running the expiration command is safe.
- Unauthorized reactivation is denied.
- Expiration and reactivation tests pass.

### Phase 7 — Usable Minimal UI

Tasks:
- Add simple navigation and dashboards appropriate to the role.
- Add forms/tables for tenant, user, course, lesson, and assignment management as required.
- Add learner course and progress screens.
- Show trial status and expiration notices.
- Use Bootstrap or existing framework styling; avoid unnecessary polish.

Acceptance criteria:
- Main required workflows can be demonstrated in a browser.
- The UI never substitutes for backend permission checks.
- Forms show useful validation errors.
- No unrelated frontend framework is introduced without approval.

### Phase 8 — Verification and Security Review

Tasks:
- Run the complete test suite.
- Review authentication and authorization paths.
- Review every endpoint that reads or mutates tenant-owned data.
- Test cross-tenant ID manipulation, role escalation, assignment consistency, expiration boundaries, and repeated expiration processing.
- Fix findings and add regression tests.
- Inspect the Git diff for accidental or unrelated changes.

Acceptance criteria:
- All tests pass, or remaining failures are clearly documented and not misrepresented.
- No known critical tenant-isolation flaw remains.
- Changed code and permission decisions are understandable to the developer.

### Phase 9 — Documentation and Submission

Tasks:
- Complete README setup/run/test instructions.
- Document architecture, role permissions, tenant isolation, trial lifecycle, and reactivation.
- The developer writes `docs/ai-course-design.md` in their own words.
- Document AI coding workflow and include this project's instructions file.
- Add safe demo setup/credentials guidance.
- Record estimated and actual time taken.
- Verify the repository can be set up from a clean checkout.

Acceptance criteria:
- All requested submission artifacts exist.
- Fresh setup instructions have been followed successfully.
- No secrets or real personal data are included.
- The developer can explain the architecture and key security choices.

## 9. Required Test Categories

At minimum, test:

- Authentication and anonymous access
- All five roles and their allowed/denied actions
- Tenant A versus Tenant B access for list, detail, update, and delete paths
- Role/tenant self-escalation attempts
- Cross-tenant course assignment
- Unassigned course access
- Cross-user progress access
- Lesson completion and progress retrieval
- Trial expiration at the exact boundary
- Scheduled expiration command run repeatedly
- Authorized and unauthorized reactivation
- Data preservation after expiry

## 10. AI Coding Workflow

For each task, the coding agent should:

1. Read this file and `Checkpoint.md`.
2. Inspect only the relevant files and tests.
3. State a concise plan and acceptance criteria before a security-sensitive or multi-file change.
4. Wait for developer approval before large or security-sensitive changes.
5. Implement one scoped change.
6. Run relevant tests and report the actual command and result.
7. Summarize changed files, security implications, and remaining work.
8. Update `Checkpoint.md` only with verified facts.
9. Leave a clean, reviewable diff.

Prefer one coding agent. Do not use subagents, external model routing, or paid APIs unless the developer explicitly approves them and a concrete need is demonstrated.

## 11. Definition of Done

The project is ready to submit when:
- The required workflows run locally.
- All five roles have documented, enforced permissions.
- Tenant isolation is tested on the backend.
- Trial expiry and reactivation work.
- Course assignments and learning progress work.
- The meaningful test suite passes.
- Migrations and setup instructions are included.
- Architecture documentation is complete.
- The developer-written AI course-generation design is included.
- Demo instructions and time estimates are recorded.
