# Permission Matrix

This document records the initial backend authorization policy. UI visibility must never be the only enforcement.

## Platform roles

| Role | Scope | Policy |
| --- | --- | --- |
| Super Admin | Platform-wide | Full platform administration, including tenant creation, tenant management, role management, and tenant reactivation. |
| Admin | Platform-wide | Administrative platform user with a defined subset of Super Admin permissions. Initial implementation: may create and view tenants and manage normal tenant accounts, but may not grant Super Admin privileges, delete tenants, or reactivate expired tenants unless explicitly added later. |
| Super Viewer | Platform-wide | Read-only user. May view explicitly permitted platform information and must not create, update, delete, reactivate, or assign records. |

## Tenant roles

| Role | Scope | Policy |
| --- | --- | --- |
| Tenant Admin | Own tenant only | Manages users, courses, lessons, assignments, and progress inside their tenant while the tenant is active. |
| Tenant User | Own tenant only | Views assigned courses/lessons and updates their own progress while the tenant is active. |

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

Tenant identity must always come from authenticated server-side user context, never from client-supplied tenant IDs.
