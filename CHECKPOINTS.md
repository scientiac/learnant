# CHECKPOINTS.md — Project Roadmap & Task Checklists

## 1. Status at a Glance
- **Overall Status:** Core MVP plus public landing, settings, and bulk learner onboarding verified (110 tests passing, Django check 0 issues).
- **Architecture:** Multi-Tenant Django Monolith (PostgreSQL ready, local SQLite fallback).
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
  - [x] Full automated test suite passing (110 tests, 0 failures)
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
- [ ] Interactive onboarding checklist banner for Tenant Admins on the dashboard (*"1. Name your institute → 2. Create course → 3. Add lessons → 4. Onboard students"*).
- [ ] Welcoming course overview card for learners guiding them directly into their syllabus.

### Group 6: AI-Powered Course Creation (Design-Only Preview)
- [ ] UI entry point / modal for Tenant Admins to input learner role, current level, goal, hours/week, and duration to see sample structured course output.
- [ ] *Human Author Task:* Developer writes `docs/ai-course-design.md` in their own words per assignment rules.
