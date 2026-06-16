"""Small shared helpers used by multiple KP services."""

from uuid import UUID

from app.core.exceptions import KpEventNotFound
from app.models.kp_event import KpEvent
from app.repositories.kp_repository import KpRepository


async def get_event_or_raise(
    repo: KpRepository, event_id: UUID, context: str = "event"
) -> KpEvent:
    """Fetch an event by ID or raise ``KpEventNotFound``."""
    event = await repo.get_by_id(event_id)
    if event is None:
        raise KpEventNotFound(f"{context}:not_found:{event_id}")
    return event
