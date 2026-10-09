# Multi-Tenant Learning Platform

A secure, minimal, multi-tenant learning platform for institutes and organizations built with Django and Django REST Framework.

---

## 1. Features & Highlights

- **Multi-Tenancy & Data Isolation:** Strict server-side scoping where tenant context is derived exclusively from authenticated user sessions. Cross-tenant ID manipulation is prevented via database constraints and 404/403 protections.
- **5-Tier Role-Based Access Control (RBAC):**
  - **Super Admin:** Platform control plus tenant-admin course, lesson, assignment, enrollment, and organization operations across active tenants; exclusive tenant reactivation.
  - **Admin:** The same tenant learning operations across active tenants, but no Super Admin grants, tenant deletion, or trial reactivation.
  - **Super Viewer:** Read-only platform-wide overview.
  - **Tenant Admin:** Manages courses, lessons, assignments, and learner progress for their institute.
  - **Tenant User:** Learner accessing assigned courses, completing lessons, and tracking progress.
- **Trial Lifecycle & Expiration:** 14-day default free trial with request-time boundary checks, idempotent scheduled expiration command (`python manage.py expire_trials`), read-only preservation of tenant data upon expiry, and Super Admin reactivation.
- **Modern UI:** shadcn/ui-inspired responsive interface built with Django templates, Tailwind CSS, and Inter typography.
- **Self-Service Onboarding:** Atomic tenant registration at `/signup/` creating an institute and Tenant Admin user in a single transaction.
- **Organization & Profile Settings:** Active Tenant Admins can update their own organization name/brand color; signed-in users can update their own display name and email.
- **Bulk Student Onboarding:** Tenant Admins can create up to 100 tenant-bound learner accounts in one submission.

---

## 2. Quickstart & Local Setup

```bash
# 1. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Or use .venv/bin/python directly

# 2. Install dependencies
pip install -r requirements.txt

# 3. Apply database migrations
python manage.py migrate

# 4. Seed demo data (creates tenants, courses, lessons, and users)
python manage.py seed_demo

# 5. Start development server
python manage.py runserver
```

Open `http://127.0.0.1:8000/` in your browser.

---

## 3. Demo Credentials

All demo accounts are created with password: `password123`.

| Username | Role | Scope | Key Capabilities |
|---|---|---|---|
| `superadmin` | Super Admin | Platform | Manage active tenant learning data; reactivate expired trials. |
| `admin` | Admin | Platform | Manage active tenant learning data; cannot reactivate trials. |
| `viewer` | Super Viewer | Platform | Read-only visibility across platform data. |
| `tenant_admin` | Tenant Admin | Demo Institute | Create/edit courses & lessons, enroll learners, view progress. |
| `institute_admin` | Tenant Admin (compatibility login) | Demo Institute | Same demo role and scope as `tenant_admin`. |
| `learner` | Tenant User | Tenant | View assigned courses, read lessons, mark completion. |

The system health check is available at `http://127.0.0.1:8000/health/`.

---

## 4. Demo Workflows

### Workflow A: Self-Signup as a New Institute
1. Navigate to `http://127.0.0.1:8000/signup/`.
2. Fill in Organisation Name, Admin Username, Email, and Password.
3. Upon submission, the organization is created on an active 14-day trial, the user is created as Tenant Admin, and logged into the dashboard immediately.

### Workflow B: Managing Courses & Assignments (Tenant Admin)
1. Log in as `tenant_admin` (or `institute_admin`).
2. Visit **Courses** (`/courses/`).
3. Click **New course** to create a course.
4. Click **Lessons** to add or edit ordered lessons.
5. Click **Assignments** to assign the course to tenant learners (e.g., `learner`).
6. Click **Progress** to review lesson completion status across enrolled learners.

### Workflow C: Learner Study & Progress
1. Log in as `learner`.
2. Visit **Courses** (`/courses/`) to see assigned courses.
3. Open a course's lessons and click **Mark Complete**.
4. Progress status updates immediately with completion timestamps.

### Workflow D: Tenant Expiration & Super Admin Reactivation
1. Run trial expiration:
   ```bash
   python manage.py expire_trials
   ```
2. For an expired tenant, tenant users and admins retain read-only access to existing data; creation and updates are blocked with friendly notices.
3. Log in as `superadmin` and navigate to **Tenants** (`/tenants/`).
4. Click **Reactivate** next to an expired tenant to restore active status with a new 14-day trial window.

### Workflow G: Platform Tenant Administration
1. Log in as `admin` or `superadmin` and open **Tenants**.
2. Select **Courses**, **Organization**, or **Enroll** on an active institute to administer that tenant's learning workspace.
3. Super Admin can additionally reactivate expired institutes. Super Viewer can open tenant courses but has no management actions.

### Workflow E: Organization & Profile Settings
1. As an active `tenant_admin`, use **Organization** to update the institute name and brand color.
2. Any signed-in user can open **Profile** to update their own first name, last name, and email. Role and tenant membership are not editable there.

### Workflow F: Bulk Student Onboarding
1. Log in as `tenant_admin` (or `institute_admin`) and open **Enroll students** (`/students/bulk-add/`).
2. Enter up to 100 usernames or email addresses, one per line.
3. Newly created learner usernames and randomly generated initial passwords are shown once after submission; share them with learners securely.

---

## 5. Testing & Verification

The Tenant Admin dashboard includes an **AI Course Assistant Preview**. It accepts learner planning inputs and renders a static sample outline only; it does not call an AI service or create/persist a course. The `docs/ai-course-design.md` document remains for the developer to write.

Run the full automated test suite (127 tests):

```bash
python manage.py test
python manage.py check
```

Test suite coverage highlights:
- `test_permissions.py`: Role matrix enforcement across all 5 roles.
- `test_phase_auth_isolation.py`: Cross-tenant boundary enforcement and ID manipulation attacks.
- `test_courses.py` & `test_lessons.py`: Scoped CRUD operations and ordering constraints.
- `test_assignments.py`: Single-tenant validation between learners and courses.
- `test_progress.py`: Learner-isolated progress updates and unassigned course access prevention.
- `test_trials.py`: Trial start/end boundaries, idempotent expiration command, and Super Admin reactivation.
- `test_web.py`: Web views, redirects, and self-signup flows.

---

## 6. Architecture & Design Documentation

Detailed documentation is available in the `docs/` directory:
- [Architecture & System Design](docs/architecture.md): Multi-tenancy approach, data isolation rules, RBAC, trial lifecycle, and data models.
- [Permissions Matrix](docs/permissions.md): Complete policy breakdown for platform and tenant roles.
- [AI Course Creation Design](docs/ai-course-design.md): Dedicated technical design document placeholder for human author completion.

---

## 7. Configuration & Database

- **Database:** PostgreSQL is the production target. Local development defaults to SQLite if `POSTGRES_DB` is not specified in the environment.
- **Environment Variables:** Copy `.env.example` to `.env` to configure PostgreSQL credentials and `SECRET_KEY`.

---

## 8. Time & Self-Deadline

- **Estimated Time:** 16 hours
- **Actual Time Taken:** ~12 hours
- **Self-Deadline:** Completed within designated window.
