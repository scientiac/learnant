# AGENTS.md

## Mission & Architecture Philosophy
Build a production-grade, secure, maintainable multi-tenant Learning Platform. Every design decision must prioritize:
1. **Zero-Trust Tenant Isolation:** Server-side scoping on every request; database constraints as the secondary shield.
2. **Production Usability:** Fully functional workflows for all 5 roles with intuitive management tools (org settings, bulk student onboarding, syllabus authoring, progress tracking).
3. **Pragmatic Full-Stack Stack:** Unified Django monolith with shadcn/ui-inspired styling (Tailwind CDN + Inter typography + CSS tokens in `base.html`), HTMX for responsive interactions, and PostgreSQL target.

---

## 1. Brand Identity & Frontend Design System (Learnant)

### Brand Identity & Ant Metaphor
- **Name:** **Learnant** (Learner + Tenant + Ant Colony metaphor).
- **Core Concept:** Multi-tenant institutes and academies operate as autonomous **Colonies** working with precision, collaborative strength, and zero-trust isolation.
- **Ant Emblem:** A minimalist, geometric line-art Ant emblem (`<svg>` with head, thorax, abdomen segments, antennae, and legs) rendered in monochrome line art as the platform mark in the navigation header, favicon, and authentication panels.
- **Colony Micro-copy:**
  - Tenant workspaces are presented as **Colony Workspaces**.
  - Users within a tenant are designated as **Colony Members**.
  - Trial lifecycle is framed as **14-Day Free Colony Trial**.
  - Subtle, witty ant touches throughout empty states and labels while maintaining 100% production-grade professionalism.

### Frontend Aesthetic: shadcn/ui Sera Style
- **Monochrome Palette:** Pure blacks (`hsl(0 0% 9%)`), crisp whites (`hsl(0 0% 100%)`), and neutral borders (`hsl(0 0% 89.8%)`) without unnecessary decorative color splashes.
- **Sharp Geometry:** Exact **0px border-radius** across all elements (buttons, cards, badges, inputs) evoking high-end architectural/developer tooling.
- **Typography:** **Inter font** with strict tracking and monospace font for role identifiers, dates, and badges (`font-mono`).
- **Iconography:** Official **Lucide Icons** (`<i data-lucide="...">`) initialized via global script and auto-refreshed upon HTMX swap events.
- **Light & Dark Mode:** Native CSS variables (`--background`, `--foreground`, `--card`, `--primary`, `--secondary`, `--muted`, `--border`, `--input`, `--ring`, `--destructive`) with `.dark` class toggle persisted in `localStorage` and system theme fallback.

### Navigation & UX Rules
- **Top Bar & Footer About Placement:** 
  - **Public / Unauthenticated:** The top navigation features a prominent, properly styled **About** button (`.btn.btn-secondary.btn-sm` with a Lucide info icon and neutral border). When on other pages, the primary "Sign in" button accompanies it; on the login page itself, the redundant sign-in link is automatically suppressed so the top bar remains clean and balanced.
  - **Authenticated:** Logged-in users already know the platform and have work to do, so the top bar keeps focus strictly on colony workspace navigation, role badge, and logout. About is subtly available via a small monospace text link in the footer (`about`).
- **Contextual Self-Signup CTA:** Rather than a distracting top-level "Sign Up" button, auth pages provide an explicit contextual box: *"Are you an institute or training academy? Sign up your organization colony here →"*.
- **Reusable Component Tokens (in `core/templates/base.html`):**
  - **Buttons:** `.btn`, `.btn-primary`, `.btn-secondary`, `.btn-destructive`, `.btn-ghost`, `.btn-outline`, `.btn-sm`
  - **Cards:** `.card` (sharp borders, monochrome card background, subtle padding)
  - **Forms:** `.form-input` (border, transparent background, ring focus), `.form-label`
  - **Badges:** `.badge`, `.badge-active`, `.badge-expired`, `.badge-suspended`, `.badge-role`
  - **Alerts:** `.alert-error`, `.alert-warning`, `.alert-info`
  - **Tables:** `.table` (`<thead>`, `<tbody>`, `<th>`, `<td>`)
  - **Nav Links:** `.nav-link`, `.nav-link.active`
  - **Separators:** `.separator` (1px neutral border)

---

## 2. Public Experience & Self-Signup Philosophy

### Who Self-Signups Make Sense For
- **Institutes / Organizations Only (Tenant Admins):** Self-signup is **exclusively** for institutes, schools, and training academies creating their dedicated organization workspace and 14-day trial.
- **Students / Learners do NOT self-signup publicly:** Learners belong to a specific institute and must be invited or enrolled by their Tenant Admin. Public student signups create orphan accounts disconnected from any school.
- **Platform Admins do NOT self-signup:** Platform roles are provisioned internally by existing Super Admins.

### Signup CTA & Frontpage Conventions
- **No Ambiguous "Sign Up" Button:** Avoid generic top-level "Sign Up" buttons that confuse learners into registering empty organizations.
- **Contextual Prompt:** Use explicit, contextual call-to-actions:
  > *"Are you an institute or training academy? Sign up your organization here."*
- **Informative Frontpage:** The unauthenticated root page (`/` or login) must **never** be a bare, isolated login box. It must feature an informative landing presentation introducing the platform, explaining what it is for, detailing multi-tenancy benefits, and providing clear paths for both existing members (Sign In) and new institutes (Sign Up).

---

## 3. Role Hierarchy & Required Pages

Every user belongs to a specific tier and must have dedicated, role-appropriate screens:

| Role | Scope | Essential Pages & Capabilities |
|---|---|---|
| **Super Admin** | Platform | Platform Dashboard, Tenant Directory (`/tenants/`), Trial Reactivation. |
| **Admin** | Platform | Platform Dashboard, Tenant Directory (Read + Create), Platform Monitoring. |
| **Super Viewer** | Platform | Read-Only Platform Dashboard, Read-Only Tenant & Course Visibility. |
| **Tenant Admin** | Tenant | Course & Lesson CRUD, Assignments & Student Roster, Bulk Student Enrollment, Progress Analytics, Organization Settings (customize institute name & branding), Profile Settings, Onboarding Setup Checklist. |
| **Tenant User** | Tenant | Assigned Courses Portal, Lesson Study Interface, One-Click Completion, Personal Progress Tracking, Profile Settings. |
| **All / Public** | Public | Informative Frontpage / Landing (`/`), Login (`/login/`), Institute Self-Signup (`/signup/`), About & Hosted Docs (`/about/`). |

---

## 4. Production Enhancements & Extension Rules

### A. Organization & Profile Management
- Tenant Admins can update their institute's display name and settings via an **Organization Settings** page.
- All authenticated users can view/update their profile (display name, email) via a **Profile** page.
- Changes must be strictly scoped to `request.user` or `request.user.tenant`.

### B. Bulk Student Onboarding
- Allow Tenant Admins to onboard students quickly (e.g., paste multi-line emails/usernames or simple bulk invite form) rather than manual one-by-one database insertion.
- Automatically assign newly created learners to `role = TENANT_USER` and `tenant = request.user.tenant`.

### C. Hosted About & Usage Documentation (`/about/`)
- Provide an in-app documentation / about page explaining how the platform works, role guides, trial lifecycle rules, and demo credentials for easy reviewer evaluation.

### D. Role-Aware Onboarding Flows
- First-time Tenant Admins receive an interactive onboarding checklist on their dashboard (*"1. Name your institute → 2. Create your first course → 3. Add lessons → 4. Onboard students"*).
- Learners receive a welcoming course overview guiding them directly into their syllabus.

### E. AI-Powered Course Creation (Design-Only Rule)
- **Design-Only Feature:** The application can include an intuitive UI entry point / preview modal (e.g., "AI Course Assistant Preview") where Tenant Admins can input learner role, current level, goal, hours/week, and duration to see sample structured course output.
- **Strict Human Author Constraint:** Do **NOT** connect to paid AI APIs. Do **NOT** generate or write the content in `docs/ai-course-design.md`. That document is strictly reserved for the human developer to write in their own words.

---

## 5. Code Organization & DRY Best Practices

Avoid code duplication across views and models:
1. **Permissions (`core/permissions.py`):** Always reuse helper functions (`is_tenant_admin`, `can_mutate_tenant_data`, `can_reactivate_tenant`). Never check raw role strings in views.
2. **Query Scoping:** Always retrieve courses via `visible_courses_for_user(request.user)`. Never query `Course.objects.all()` in tenant-facing views.
3. **Form-Level Isolation:** Any form selecting related objects (e.g., students) must accept `tenant=request.user.tenant` and filter querysets to that tenant only.
4. **Database Relational Integrity:** Enforce compound unique constraints (`UniqueConstraint`) and model `clean()` validations on all related models.

---

## 6. Security & Isolation Invariants (Non-Negotiable)
- **Zero Trust on Client IDs:** Tenant identity is strictly derived from `request.user.tenant`. Never accept a `tenant_id` from client POST/GET parameters.
- **IDOR Immunity:** Accessing another tenant's course, lesson, or student via URL ID must return HTTP 404 (or 403), never leaking foreign records.
- **Trial Expiration:** Enforced at request time via `can_mutate_tenant_data()` AND via the idempotent command `python manage.py expire_trials`.
- **Data Preservation:** Expired tenants remain read-only; records are never deleted upon trial expiration.

---

## 7. Efficient Agent Workflow & Checklist Policy
- **Checkpoints File:** Keep `CHECKPOINTS.md` simple, clear, and actionable using task checkboxes. Do NOT waste tokens writing long narrative essays in checkpoint files. Focus on writing clean code and running tests.
- **Always Test:** Every change must be validated with `.venv/bin/python manage.py test` and `python manage.py check`. Never claim a test passed without running it.
