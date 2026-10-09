from .models import Tenant, User


PLATFORM_ROLES = {
    User.Role.SUPER_ADMIN,
    User.Role.ADMIN,
    User.Role.SUPER_VIEWER,
}
TENANT_ROLES = {
    User.Role.TENANT_ADMIN,
    User.Role.TENANT_USER,
}
MUTATING_METHODS = {'POST', 'PUT', 'PATCH', 'DELETE'}
SAFE_METHODS = {'GET', 'HEAD', 'OPTIONS'}


def is_platform_user(user):
    return bool(user and user.is_authenticated and user.role in PLATFORM_ROLES)


def is_super_admin(user):
    return bool(user and user.is_authenticated and user.role == User.Role.SUPER_ADMIN)


def is_admin(user):
    return bool(user and user.is_authenticated and user.role == User.Role.ADMIN)


def is_platform_admin(user):
    """Platform staff who can administer tenant learning content."""
    return is_super_admin(user) or is_admin(user)


def is_super_viewer(user):
    return bool(user and user.is_authenticated and user.role == User.Role.SUPER_VIEWER)


def is_tenant_admin(user):
    return bool(user and user.is_authenticated and user.role == User.Role.TENANT_ADMIN)


def is_tenant_user(user):
    return bool(user and user.is_authenticated and user.role == User.Role.TENANT_USER)


def can_manage_platform(user):
    return is_super_admin(user) or is_admin(user)


def can_reactivate_tenant(user):
    return is_super_admin(user)


def can_read_platform(user):
    return is_platform_user(user)


def can_manage_tenant(user, tenant):
    """Whether the role may administer this tenant, independent of trial status."""
    if not user or not user.is_authenticated or tenant is None:
        return False
    if is_platform_admin(user):
        return True
    return is_tenant_admin(user) and user.tenant_id == tenant.id


def can_mutate_tenant_data(user, tenant=None):
    """Allow tenant administrators or platform admins to write active tenant data."""
    if not user or not user.is_authenticated:
        return False
    if user.role in TENANT_ROLES:
        if not user.tenant_id:
            return False
        if tenant is not None and tenant.id != user.tenant_id:
            return False
        tenant = user.tenant
    elif not is_platform_admin(user) or tenant is None:
        return False
    return tenant.status == Tenant.Status.ACTIVE and not tenant.is_trial_expired()


def can_manage_tenant_learning(user, tenant):
    return can_manage_tenant(user, tenant) and can_mutate_tenant_data(user, tenant)


def can_read_tenant_data(user, tenant):
    if not user or not user.is_authenticated or not tenant:
        return False
    if is_platform_user(user):
        return True
    return user.role in TENANT_ROLES and user.tenant_id == tenant.id


def can_use_tenant_request_method(user, method):
    if method in SAFE_METHODS:
        return bool(user and user.is_authenticated and user.role in TENANT_ROLES and user.tenant_id)
    if method in MUTATING_METHODS:
        return can_mutate_tenant_data(user)
    return False
