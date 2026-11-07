from collections.abc import Sequence
from typing import Optional
from uuid import UUID

from app.core.auth_context import require_kp_president_user
from app.core.exceptions import KpEventNotFound, KpNameExists
from app.models.kp_event import KpEvent
from app.schemas.kp import CloneKpInput, CreateKpInput, UpdateKpInput
from app.services.kp_service.base import KpServiceBase


class EventsMixin(KpServiceBase):
    async def _ensure_event_name_free(self, name: str, context: str) -> None:
        if await self.kp_repository.get_by_name(name) is not None:
            raise KpNameExists(f"{context}:{name}")

    async def list_kps(self) -> Sequence[KpEvent]:
        return await self.kp_repository.list_kps()

    async def get_latest_kp(self) -> Optional[KpEvent]:
        return await self.kp_repository.get_latest_kp()

    async def get_event_by_id(self, event_id: UUID) -> KpEvent:
        return await self._get_event(event_id)

    async def get_event_settings(self, event_id: UUID) -> KpEvent:
        require_kp_president_user(self.current_user)
        return await self._get_event(event_id)

    async def create_kp(self, create_kp_input: CreateKpInput) -> KpEvent:
        require_kp_president_user(self.current_user)
        await self._ensure_event_name_free(create_kp_input.name, "create_kp")
        return await self.kp_repository.create_kp(create_kp_input)

    async def clone_kp(self, event_id: UUID, clone_kp_input: CloneKpInput) -> KpEvent:
        require_kp_president_user(self.current_user)
        await self._ensure_event_name_free(clone_kp_input.name, "clone_kp")
        cloned_event = await self.kp_repository.clone_kp(event_id, clone_kp_input)
        if cloned_event is None:
            raise KpEventNotFound(f"event:not_found:{event_id}")
        return cloned_event

    async def update_kp(
        self, event_id: UUID, update_kp_input: UpdateKpInput
    ) -> KpEvent:
        require_kp_president_user(self.current_user)
        updates = update_kp_input.model_dump(exclude_unset=True)
        event = await self._get_event(event_id)
        new_name = updates.get("name")
        if new_name is not None and new_name != event.name:
            await self._ensure_event_name_free(new_name, "update_kp")
        return await self.kp_repository.update_kp(
            event=event, update_kp_input=update_kp_input
        )
