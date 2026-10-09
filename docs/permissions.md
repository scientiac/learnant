# Permission Matrix

This document records the initial backend authorization policy. UI visibility must never be the only enforcement.

## Platform roles

| Role | Scope | Policy |
| --- | --- | --- |
| Super Admin | Platform-wide | Highest privilege. Inherits platform Admin and Tenant Admin management actions across active tenants: create tenants and initial Tenant Admins, manage courses/lessons/learner accounts/assignments, organization settings and progress; provision Admin/Super Viewer accounts; and reactivate expired tenants. Deployment bootstrap provisions the first Super Admin. |
| Admin | Platform-wide | Inherits Tenant Admin learning and learner-account management across active tenants, and may create tenants with an initial Tenant Admin. Cannot grant platform roles, delete platform tenants, or reactivate expired tenants. |
| Super Viewer | Platform-wide | Read-only visibility across tenants, courses, lessons, assignments, and progress. Cannot create, update, delete, assign, enroll, or reactivate. |

## Tenant roles

| Role | Scope | Policy |
| --- | --- | --- |
| Tenant Admin | Own tenant only | Manages users, courses, lessons, assignments, and progress inside their tenant while the tenant is active. |
| Tenant User | Own tenant only | Views assigned courses/lessons and updates their own progress while the tenant is active. |

## Permission inheritance

Platform Admin and Super Admin can perform tenant-admin management operations for a selected tenant from the platform tenant directory or global course directory. The target tenant is resolved server-side from a validated URL/form selection. Tenant Admins remain scoped to their authenticated tenant. Super Viewer can inspect the same platform content but receives no mutation controls or permissions. Platform roles do not impersonate learners or create learner progress on a learner's behalf; learners alone mark their own assigned lessons complete.

Tenant Admins can view and update only Tenant User accounts inside their own tenant; update forms cannot change role or tenant. Deactivation preserves course assignments and progress. Super Admin provisions platform Admin and Super Viewer accounts individually; Tenant Admins cannot create platform roles.

All tenant-scoped writes—including writes by platform staff—are blocked when the target tenant is expired or its trial boundary has passed.

## Expired tenant policy

When a tenant expires, its existing data is preserved and becomes read-only to tenant users.

Allowed after expiry:
- Tenant users and tenant admins may view existing data they were already authorized to access.
- Platform users with appropriate permissions may view expired tenant records.
- Super Admin may reactivate a tenant.

Restricted after expiry:
- Tenant users may not create or update learning progress.
- Tenant admins may not create, update, delete, assign, or revoke tenant learning records.
- No tenant-scoped user may add new data to the expired tenant.

Reactivation policy:
- Only Super Admin can reactivate an expired tenant.
- Reactivation sets the tenant back to active, clears `expired_at`, and starts a new 14-day trial from the reactivation time.
- Existing tenant data is preserved during expiration and reactivation.
- Only Super Admin can switch subscription status or adjust the exact trial end; subscribed tenants do not expire through the trial command.

Tenant identity must always come from authenticated server-side user context, never from client-supplied tenant IDs.
