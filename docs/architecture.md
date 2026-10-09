# Architecture & System Design Documentation

This document describes the architectural decisions, security boundaries, and lifecycle management for the Multi-Tenant Learning Platform.

---

## 1. Multi-Tenancy Model

### Selected Approach: Shared Database, Shared Schema with Tenant Scoping
- **Why this approach?**
  - High operational simplicity and maintainability for an educational SaaS platform serving multiple institutes.
  - Native Django ORM integration with standard database migrations.
  - Low infrastructural overhead compared to database-per-tenant or schema-per-tenant architectures, while achieving equivalent logical isolation.
- **Tenant Entity:**
  - The `Tenant` model represents an individual institute or organisation.
  - Every tenant-scoped entity (`User`, `Course`, `CourseAssignment`) maintains a foreign key to `Tenant`.

---

## 2. Server-Side Data Isolation & Security

### Zero Trust on Client Input
- **Tenant Context Derivation:**
  - The user's active tenant is **never** accepted from query parameters, request bodies, or URL paths.
  - The tenant is strictly derived from the authenticated session (`request.user.tenant`).
- **Scoping & Object Access:**
  - All queries for tenant resources are filtered server-side by `visible_courses_for_user(request.user)` or explicit tenant foreign keys.
  - Cross-tenant ID manipulation (IDOR) attempts via URL path parameters return HTTP 404 (Not Found) or HTTP 403 (Forbidden), preventing information leakage.
- **Relational Integrity via Database Constraints:**
  - `CourseAssignment` enforces uniqueness across `(tenant, course, learner)` and validates in `clean()` that both learner and course belong to the assignment's tenant.
  - `LessonProgress` enforces uniqueness across `(assignment, lesson)` and validates in `clean()` that the lesson belongs to the assigned course.
  - `Course` enforces unique titles per tenant `(tenant, title)`.
  - `Lesson` enforces unique ordering and unique titles per course `(course, order)` and `(course, title)`.
  - `User` enforces role-tenant consistency using check constraints (`user_role_tenant_membership_valid`).

---

## 3. Role-Based Access Control (RBAC)

The system defines 5 roles across two distinct scopes (Platform vs. Tenant):

| Scope | Role | Permissions |
|---|---|---|
| **Platform** | **Super Admin** | Bootstrap-provisioned highest role: create tenants, manage tenant learning/user records, provision Admin/Super Viewer, subscription controls, and trial reactivation. |
| **Platform** | **Admin** | Create tenants and administer tenant learning/user records across active tenants; cannot provision platform roles, delete tenants, or reactivate trials. |
| **Platform** | **Super Viewer** | Platform-wide read-only visibility: view tenant list, courses, and progress across the platform without write/edit access. |
| **Tenant** | **Tenant Admin** | Institute manager: create and manage courses, lessons, assignments, and view learner progress inside their own tenant. |
| **Tenant** | **Tenant User** | Learner: view assigned courses, study lessons, and record progress/completion on their own assignments. |

All authorization rules are enforced in views and models on the server, independent of UI representation.

The first Super Admin is created with `python manage.py bootstrap_superadmin` using deployment environment secrets. The command is idempotent; provisioned Super Admins, Admins, and Super Viewers must change their temporary password before using the platform. Tenant Admins can edit/deactivate only learner accounts in their own tenant. Deactivation preserves assignments and progress.

---

## 4. Tenant Trial Lifecycle & Expiration

```
[ Tenant Created ] ──> [ Trial Active (14 Days) ] ──> [ Expired (Read-Only) ]
                                                            │
                                                     Super Admin Reactivates
                                                            │
                                                            ▼
                                                   [ Trial Active (14 Days) ]
```

### 1. Calculation
- When a tenant is created, `trial_starts_at` defaults to `timezone.now()`.
- `trial_ends_at` defaults to `trial_starts_at + 14 days` (configurable via `DEFAULT_TRIAL_DAYS`).

### 2. Request-Time Boundary Check
- During every mutating operation (`can_mutate_tenant_data(user, tenant)`), the system checks the authenticated tenant or explicitly authorized platform target:
  ```python
  tenant.status == Tenant.Status.ACTIVE and not tenant.is_trial_expired()
  ```
  where `is_trial_expired()` verifies `now >= trial_ends_at` only for Trial subscriptions; Subscribed tenants do not expire through the trial command.
- Even if a background expiration task has not yet run, expired tenants are immediately restricted upon hitting the exact expiration timestamp.

### 3. Background Expiration Command (`expire_trials`)
- Idempotent Django management command: `python manage.py expire_trials`.
- Finds active Trial tenants whose `trial_ends_at <= timezone.now()`, sets `status = Tenant.Status.EXPIRED`, and records `expired_at`.
- Running repeatedly produces zero adverse side effects.

### 4. Data Preservation
- When a tenant expires, existing users, courses, assignments, and completion records are preserved.
- Tenant users and administrators can still view existing data in read-only mode, but cannot create or mutate courses, assignments, or progress records.

### 5. Reactivation
- Only **Super Admin** can reactivate a tenant (`tenant.reactivate()`).
- Reactivation restores status to `ACTIVE`, resets `trial_starts_at` to current timestamp, grants a new 14-day trial window, and clears `expired_at`.

---

## 5. Frontend & UI Architecture

- **Stack:** Server-rendered Django templates styled with a shadcn/ui-inspired design system using Tailwind CSS and Inter typography via CDN.
- **Component Classes:** Standardized CSS tokens and component classes (`.btn`, `.btn-primary`, `.card`, `.form-input`, `.badge`, `.table`, `.alert-error`) defined in `base.html` for maintainability.
- **Progressive Enhancement:** HTMX integration ready for dynamic interactions.
- **Self-Service Onboarding:** Atomic tenant registration via `/signup/` allowing new institutes to register and receive immediate Tenant Admin access.

---

## 6. Testing Strategy

- **Test Suite:** 199 automated test cases spanning:
  - Role-based permissions (`test_permissions.py`)
  - Cross-tenant data isolation and ID manipulation (`test_phase_auth_isolation.py`)
  - Course and lesson CRUD boundaries (`test_courses.py`, `test_lessons.py`)
  - Course assignments and tenant consistency (`test_assignments.py`)
  - Learner progress tracking and cross-user isolation (`test_progress.py`)
  - Trial expiration boundaries and idempotency (`test_trials.py`)
  - Web flows, signup, and authentication redirects (`test_web.py`)
  - Deployment bootstrap, platform account provisioning, tenant learner management, CSV enrollment, and first-login password reset
  - Container environment parsing and production settings

---

## 7. Production Roadmap & Architectural Extensions

### 1. Robust Lesson Sequence Management
- **Collision Prevention:** Default order calculated via `max(order) + 1` to eliminate `IntegrityError` collisions on `(course_id, order)`.
- **Reordering Subsystem:** Dedicated drag-and-drop / swap interface utilizing atomic multi-step buffer transactions to safely reorder syllabus modules.

### 2. Rich Content & Dedicated Lesson Study Environment
- **Dedicated Study View:** Individual lesson route (`/courses/<course_id>/lessons/<lesson_id>/`) with progress toggling and syllabus outline.
- **GFM & LaTeX Engine:** Client-side KaTeX + GFM Markdown rendering for technical, mathematical, and rich textual course material.
- **Video Embeds:** YouTube/Vimeo/direct video URLs plus repeatable uploaded video assets with Markdown references.

### 3. Dynamic Onboarding Engine ("Set up your colony")
- Self-hiding state checklist evaluating colony setup progress: name review, initial course creation, lesson authoring, and learner onboarding.

### 4. Enterprise Subscription & Expiration Controls
- Super Admin controls to toggle between `trial` and `subscribed` status.
- Granular expiration adjustment allowing positive or negative time deltas (e.g. +10 mins, +10 months, or shortening active duration).

### 5. Resilient Spreadsheet Ingestion
- CSV template export and fault-tolerant batch importer assigning users to `TENANT_USER` with optional course associations.

### 6. Portable Container Architecture (Django + PostgreSQL)
- Docker Compose runs the application and PostgreSQL in separate services, with durable named volumes for relational data and uploads.
- The application uses PostgreSQL in container deployments; local debug-only SQLite remains available for quick direct development.
- The image starts with migrations and WhiteNoise static collection, then serves Django via Gunicorn; `/health/` is the container health check.
- GitHub Actions publishes multi-architecture images to GHCR on branch and version-tag pushes, and signs published image digests with keyless Cosign.
- Production requires a strong secret, database configuration, and allowed-host list. Live PostgreSQL deployment must be verified against the deployment host's managed or self-hosted service.
