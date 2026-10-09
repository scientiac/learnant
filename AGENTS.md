# AGENTS.md

## Mission
Build the **smallest complete, secure, maintainable** version that meets the assignment. Prefer working, understandable code over cleverness or extra features.

## Frontend Design System

The UI uses a **shadcn/ui-inspired design system** implemented with Tailwind CSS CDN and Inter font (Google Fonts). All design tokens and reusable component classes are defined in `core/templates/base.html` — do NOT use ad hoc Tailwind classes in individual templates.

### Available CSS classes (defined in base.html `<style>` block)
- **Buttons:** `.btn`, `.btn-primary`, `.btn-secondary`, `.btn-destructive`, `.btn-ghost`, `.btn-outline`, `.btn-sm`
- **Cards:** `.card` (white rounded card with border and shadow)
- **Forms:** `.form-input` (use in all form widget attrs), `.form-label`
- **Badges:** `.badge`, `.badge-active` (green), `.badge-expired` (red), `.badge-suspended` (amber), `.badge-role` (blue)
- **Alerts:** `.alert-error`, `.alert-warning`, `.alert-info`
- **Tables:** `.table` (use on `<table>` with `<thead>`, `<tbody>`, `<th>`, `<td>`)
- **Nav links:** `.nav-link`, `.nav-link.active`

### Template block conventions
- `{% block nav_courses %}active{% endblock %}` — marks Courses nav link active
- `{% block nav_tenants %}active{% endblock %}` — marks Tenants nav link active

### Signup flow
- `GET/POST /signup/` → `core.views.signup` → `registration/signup.html`
- `TenantSignupForm` in `core/forms.py` creates a Tenant and Tenant Admin user atomically (using `transaction.atomic`)
- Authenticated users visiting `/signup/` are redirected to dashboard
- After successful signup the user is logged in automatically

### Do not
- Add new raw Tailwind classes to templates — use the existing component classes
- Use `|split` or other non-standard Django template filters
- Change the color palette without updating the CSS variables block in `base.html`


## Before editing
1. Read `PLANS.md`, `Checkpoint.md`, and the assignment brief if present.
2. Inspect the existing repository, `git status --short`, Python version, and installed project conventions. Do not assume files, tools, or services exist.
3. Continue only the current phase in `Checkpoint.md`. Choose one small task at a time; do not build the whole roadmap in one pass.
4. If the repository already works, preserve its structure. Do not rewrite it just to match a preference.

## Keep it simple and compatible
- Target the system's installed Python and available tools. Work in a virtual environment; never modify system Python packages.
- Use Django + Django REST Framework and PostgreSQL for the intended app. Keep local setup practical; SQLite is acceptable for local tests/development when configured, but document PostgreSQL as the target.
- Add the fewest dependencies possible. Check whether a package is already available before adding one. Do not add Docker, services, frameworks, or abstractions unless necessary.
- Use clear, idiomatic Django code and existing project conventions. Prefer explicit code over generic helper layers, repositories, factories, or premature abstraction.
- Read only relevant files and search targeted paths. Avoid dumping large files or repeatedly re-reading unchanged context.

## Security requirements
- Enforce every role permission on the **server**, not just in the UI. Deny access by default.
- Derive the tenant from the authenticated user on the server. Never trust a client-supplied tenant ID, role, or ownership claim.
- Scope every tenant-owned list, detail, update, delete, nested-resource, assignment, and progress query to the user's authorized tenant. Validate that related objects belong to the same tenant.
- Prevent cross-tenant ID manipulation (IDOR). Test access by changing object IDs; do not leak another tenant's data in responses or errors.
- Keep Super Viewer read-only. Learners may access only assigned courses and their own progress. Follow `PLANS.md` for the agreed role matrix; do not invent extra privileges.
- Keep secrets in environment variables; never commit passwords, tokens, or real personal data.

## Data and trial lifecycle
- Use database constraints and validation where useful; create and commit migrations for model changes.
- Trial expiration must be enforced during protected requests and by a safe, repeatable, idempotent command or job. Preserve tenant data after expiration; only an authorized action may reactivate a trial.
- Do not add payments or a real AI integration. AI-powered course creation is design-only. **Do not write the AI design/documentation content**; leave that section for the human author and only add a clearly marked placeholder if needed.

## Change and test workflow
1. Make the smallest change that completes the current task.
2. Add/update focused tests for changed behavior, especially permissions and tenant isolation.
3. Run relevant tests, then the broader test suite when practical. Also run `python manage.py check` and `git diff --check` when applicable.
4. Review `git diff --stat` and `git diff`. Remove unrelated edits, debug code, dead code, and accidental secrets.
5. Never claim a test passed unless you ran it and saw it pass. If something cannot run, state the exact blocker and command.

Required coverage includes role permissions, cross-tenant access, course assignment, progress ownership, and trial expiration/idempotency.

## Token-efficient agent behavior
- Avoid unnecessary web calls, long explanations, broad refactors, duplicate tests, and speculative features.
- Before changing code, identify the relevant files and the intended minimal change. Ask a question only when a missing decision blocks safe progress; otherwise use documented project decisions.
- Keep command output focused. Do not print secrets or large environment dumps.
- Update `Checkpoint.md` after each completed task: what changed, commands/tests and actual results, known issues, and the single next task. Update `PLANS.md` only when the plan itself genuinely changes.

## Done means
The app runs with documented setup; migrations are current; changed behavior has tests; role checks and tenant isolation are enforced server-side; relevant checks were actually run; docs and `Checkpoint.md` reflect reality. Finish with a concise report of changed files, exact test results, and any remaining blocker.
