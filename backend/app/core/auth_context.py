from dataclasses import dataclass
from uuid import UUID

from app.core.config import get_settings
from app.core.exceptions import EmailNotConfirmed, NotAllowed, UserNotConfirmed
from app.models.user import User


@dataclass(frozen=True)
class AuthorizedUser:
    user: User


@dataclass(frozen=True)
class ConfirmedCompanyUser(AuthorizedUser):
    pass


@dataclass(frozen=True)
class AssignedCompanyUser(ConfirmedCompanyUser):
    company_id: UUID


@dataclass(frozen=True)
class StaffUser(AuthorizedUser):
    pass


@dataclass(frozen=True)
class AdminUser(StaffUser):
    pass


@dataclass(frozen=True)
class KpPresidentUser(AuthorizedUser):
    role: str


def require_confirmed_company_user(user: User) -> ConfirmedCompanyUser:
    if not user.is_company:
        raise NotAllowed(f"require_confirmed_company:{user.id}")
    if not user.email_confirmed:
        raise EmailNotConfirmed(f"require_confirmed_company:{user.id}")
    if not user.user_confirmed:
        raise UserNotConfirmed(f"require_confirmed_company:{user.id}")
    return ConfirmedCompanyUser(user=user)


def require_assigned_company_user(user: User) -> AssignedCompanyUser:
    require_confirmed_company_user(user)
    if user.company_id is None:
        raise NotAllowed(f"require_assigned_company:{user.id}")
    return AssignedCompanyUser(user=user, company_id=user.company_id)


def require_kp_president_user(user: User) -> KpPresidentUser:
    role = get_settings().VISIT_KP_PRESIDENT_ROLE
    user_roles = {user_role.name for user_role in (user.roles or [])}
    if role not in user_roles and not user.is_admin:
        raise NotAllowed(f"require_role[{role}]:{user.id}")
    return KpPresidentUser(user=user, role=role)


def require_staff_user(user: User) -> StaffUser:
    if not user.is_staff and not user.is_admin:
        raise NotAllowed(f"require_staff:{user.id}")
    return StaffUser(user=user)


def require_admin_user(user: User) -> AdminUser:
    if not user.is_admin:
        raise NotAllowed(f"require_admin:{user.id}")
    return AdminUser(user=user)
