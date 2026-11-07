from uuid import UUID

from app.core.exceptions import KpEventNotFound
from app.models.kp_event import KpEvent
from app.repositories.kp_repository import KpRepository


async def require_event(
    kp_repository: KpRepository, event_id: UUID, identifier: str
) -> KpEvent:
    event = await kp_repository.get_by_id(event_id)
    if event is None:
        raise KpEventNotFound(identifier)
    return event


async def require_locked_event(
    kp_repository: KpRepository, event_id: UUID, identifier: str
) -> KpEvent:
    event = await kp_repository.lock_model_by_id(KpEvent, event_id)
    if event is None:
        raise KpEventNotFound(identifier)
    return event
