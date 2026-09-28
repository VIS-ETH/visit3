from uuid import UUID

from app.core.dates import local_today
from app.repositories.kp_repository import KpRepository


async def has_registration_exception(
    kp_repository: KpRepository, event_id: UUID, company_id: UUID
) -> bool:
    exception = await kp_repository.get_registration_exception(event_id, company_id)
    return exception is not None and exception.allowed_until >= local_today()
