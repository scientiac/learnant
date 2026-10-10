# CHECKPOINTS.md — Project Roadmap & Task Checklists

## 1. Status at a Glance
- **Overall Status:** Portable Docker deployment and environment handling implemented (207 tests passing, Django check 0 issues).
- **Architecture:** Multi-Tenant Django Monolith (PostgreSQL in container deployments, local SQLite fallback).
- **Design System:** shadcn/ui-inspired responsive interface (Tailwind CDN + Inter typography).
- **Quick Run:**
  ```bash
    .venv/bin/python manage.py test        # Run all automated tests
  .venv/bin/python manage.py runserver   # Launch development server
  ```

---

## 2. Completed Milestones

- [x] **Phase 0 — Project & Repo Setup**
  - [x] Custom User model & PostgreSQL / SQLite configuration
  - [x] Health check endpoint (`/health/`)
  - [x] Git repository initialized and checkpointed
- [x] **Phase 1 — Tenant & User Foundations**
  - [x] 5-tier role hierarchy (Super Admin, Admin, Super Viewer, Tenant Admin, Tenant User)
  - [x] Database check constraints for role-tenant validity
- [x] **Phase 2 — Authentication & Authorization**
  - [x] Server-side permissions matrix (`core/permissions.py`)
  - [x] Role-aware login/logout flows and protected URL redirects
- [x] **Phase 3 — Tenant Isolation & IDOR Protection**
  - [x] Context-derived query scoping (`visible_courses_for_user`)
  - [x] Cross-tenant URL ID manipulation returns 404/403
- [x] **Phase 4 — Courses, Lessons & Assignments**
  - [x] Course CRUD within authorized tenant
  - [x] Ordered lesson syllabus management
  - [x] Course assignment and same-tenant student validation
- [x] **Phase 5 — Learning Progress**
  - [x] Learner one-click lesson completion tracking
  - [x] Instructor aggregate progress analytics
- [x] **Phase 6 — Trial Lifecycle & Expiration**
  - [x] 14-day default free trial with request-time boundary checks
  - [x] Idempotent expiration management command (`python manage.py expire_trials`)
  - [x] Read-only data preservation & Super Admin reactivation
- [x] **Phase 7 — Frontend Redesign & Public Signup**
  - [x] Complete template redesign with shadcn/ui design tokens
  - [x] Public atomic organization sign-up flow (`/signup/`)
  - [x] Comprehensive documentation (`docs/WHATISIT.md`, `docs/architecture.md`, `README.md`)
- [x] **Phase 8 — Verification & Security Review**
  - [x] Full automated test suite passing (190 tests, 0 failures)
- [x] **Phase 9 — Brand Identity & shadcn Sera Monochrome Overhaul**
  - [x] **Learnant** branding (Learner + Tenant + Ant Colony metaphor) with custom geometric line-art Ant emblem
  - [x] shadcn/ui Sera aesthetic: monochrome (black & white), sharp 0px corners, Inter font, official Lucide icons
  - [x] Light and dark mode support with localStorage persistence and system fallback
  - [x] Contextual self-signup prompt and elimination of redundant top-bar "Log in" button on login page
  - [x] Complete template modernization across all views (dashboard, courses, lessons, assignments, progress, tenants, confirmation modals)

---

## 3. Upcoming Production Enhancements

### Group 1: Public Frontpage & Self-Signup CTA Refinement
- [x] Informative public landing page at `/` (explaining multi-tenancy and platform features) instead of a bare login card.
- [x] Refine signup CTA with explicit organization-only language on landing, login, and signup pages.

### Group 2: Organization Settings & Profile Customization
- [x] Organization Settings page (`/settings/organization/`) for Tenant Admins to customize institute name & branding.
- [x] User Profile Settings page (`/settings/profile/`) for all authenticated users to view/update display name and email.

### Group 3: Bulk Student Onboarding
- [x] Bulk student onboarding interface (`/students/bulk-add/`) allowing Tenant Admins to onboard learners in bulk via multi-line text (usernames/emails).
- [x] Automatically assign newly created learners to `role = TENANT_USER` and `tenant = request.user.tenant`.

### Group 4: Hosted About & Usage Documentation Screen
- [x] In-app `/about/` page detailing platform architecture, 5-tier role guide, trial lifecycle rules, and reviewer credentials.
- [x] Add About link to both public and authenticated navigation headers.

### Group 5: Role-Aware Onboarding Setup Guidance
- [x] Interactive onboarding checklist banner for Tenant Admins on the dashboard (*"1. Name your institute → 2. Create course → 3. Add lessons → 4. Onboard students"*).
- [x] Welcoming course overview card for learners guiding them directly into their syllabus.

### Group 6: AI-Powered Course Creation (Design-Only Preview)
- [x] UI entry point / preview for Tenant Admins to input learner role, current level, goal, hours/week, and duration to see static sample structured course output.
- [ ] *Human Author Task:* Developer writes `docs/ai-course-design.md` in their own words per assignment rules.

---

## 4. Next Milestones & Production Upgrades

### Priority 1: Lesson Unique Order Collision Bug Fix & Reorder Mode
- [x] Fix `IntegrityError (UNIQUE constraint failed: core_lesson.course_id, core_lesson.order)` on `/courses/<id>/lessons/new/`.
- [x] Automatically assign next sequence position (`max(order) + 1`) by default on lesson creation.
- [x] Introduce lesson reordering controls with transactional buffer ordering to prevent intermediate unique collisions.

### Priority 2: Dynamic Colony Onboarding Checklist ("Set up your colony")
- [x] Short onboarding checklist on Tenant Admin dashboard:
  - [x] Organization naming is complete at required organization signup; settings remain linked when the name is missing.
  - [x] "Create your first course" — auto-hides once a course exists.
  - [x] "Add your first lesson" — auto-hides once a lesson exists in the tenant.
  - [x] "Onboard your first learner" — auto-hides once a learner exists.

### Priority 3: Dedicated Lesson Study View & Rich Content (GFM + LaTeX + Video)
- [x] Dedicated individual lesson study page (`/courses/<course_id>/lessons/<lesson_id>/`) with syllabus navigation.
- [x] Rich document support: GitHub-Flavored Markdown (GFM) with images and LaTeX math equations (KaTeX).
- [x] Lesson lists show title and description without content previews.
- [x] Add images/videos one at a time; uploaded references insert into Markdown immediately and multiple videos per lesson are supported.
- [x] Document persistent `/app/uploads` storage required to preserve files between container rebuilds.

### Priority 4: Student First-Login Password Reset
- [x] Add `must_change_password` flag to User model (default `True` for new learners; existing/demo accounts preserved).
- [x] Redirect provisioned learners to set a secure password before accessing the application; permit password change or logout.

### Priority 5: Flexible Subscription & Expiration Control (Super Admin)
- [x] Super Admin ability to switch tenant between `trial` and `subscribed` status.
- [x] Granular time adjustments: set exact trial end or grant/reduce minutes, hours, days, or months.

### Priority 6: User Avatars & Extended Organization Details
- [x] Profile image upload for user profiles.
- [x] Organization logo / branding image upload.
- [x] Organization public details for students (address, contact number, support email, website).

### Priority 7: Fail-Proof Spreadsheet Bulk Enrollment (CSV/Excel)
- [x] Exportable sample spreadsheet template (`.csv`).
- [x] Robust CSV import parser with independent row validation and duplicate-safe skips.
- [x] Support enrolling learners with or without immediate same-tenant course assignments.

### Priority 8: Portable Container Deployment (PostgreSQL + Django)
- [x] Portable Docker deployment with PostgreSQL Compose service, persistent volumes, Gunicorn, and WhiteNoise.
- [x] Environment variable specifications (`DATABASE_URL`, `SECRET_KEY`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`).
- [x] GitHub Actions multi-architecture GHCR publishing and keyless Cosign image signing.
- [x] Railway deployment defaults to production and refuses to fall back to ephemeral SQLite.
- [x] README step-by-step deployment guide covers PostgreSQL linking, required secrets, Super Admin bootstrap, and database verification.
- [x] Documented that bootstrap credentials must be followed by an explicit management command and that existing usernames are not password-reset by rerunning it.
- [x] Allow the `learnant.3o14.com` hostname and HTTPS origin.
- [ ] PostgreSQL service connectivity could not be exercised locally; verify against the target host's PostgreSQL service at deployment.

### Priority 9: Remaining Take-Home Submission Items
- [x] Add platform-side tenant creation for Admin/Super Admin with an initial Tenant Admin.
- [x] Add Tenant Admin-scoped learner roster edit and activate/deactivate management.
- [x] Add deployment-time Super Admin bootstrap with forced password change.
- [x] Add Super Admin single-account provisioning for Admin/Super Viewer with forced password change.
- [x] Add the missing organization admin email field to self-signup and correct signup guidance.
- [x] Replace production demo-account details on About with product overview, workflow, role guide, and production access information.
- [x] Add self-service password changes in account settings for platform and tenant users.
- [x] Add tenant-scoped search for courses, lessons, member rosters, assignments, and progress; add platform search for colonies, owners, and all colony members.
- [x] Show Tenant Admin/owner accounts to platform roles in colony and read-only member directories.
- [x] Document the manual Railway redeploy step after GHCR publishing; no Railway token is required.
- [x] Reconcile architecture/permissions docs and test counts with current implementation.
- [ ] Record the original self-deadline if known; it cannot be reconstructed from the repository.
- [ ] Human developer completes `docs/ai-course-design.md`; do not generate its content.
