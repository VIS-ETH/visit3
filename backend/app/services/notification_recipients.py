from collections.abc import Sequence

from app.core.config import get_settings
from app.models.kp_event import KpEvent
from app.repositories.kp_repository import KpRepository


class NotificationRecipients:
    def __init__(self, kp_repository: KpRepository) -> None:
        self.kp_repository = kp_repository

    def _relevant_event(self, events: Sequence[KpEvent]) -> KpEvent | None:
        open_event = next(
            (event for event in events if event.is_registration_open()), None
        )
        if open_event is not None:
            return open_event
        return events[0] if events else None

    async def staff_notification_email(self) -> str:
        event = self._relevant_event(await self.kp_repository.list_kps())
        configured = event.notification_email if event is not None else None
        if configured and configured.strip():
            return configured.strip()
        return get_settings().DEFAULT_NOTIFICATION_EMAIL
