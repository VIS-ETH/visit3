from collections.abc import Sequence
from uuid import UUID

from app.core.auth_context import require_assigned_company_user, require_staff_user
from app.core.exceptions import KpNametagLimitReached, KpNametagsDeadlinePassed
from app.models.kp_event import KpEventBooking, NameTag
from app.schemas.kp import NameTagInput, NameTagResult
from app.services.kp_service.base import KpServiceBase


def name_tag_result(name_tag: NameTag) -> NameTagResult:
    return NameTagResult(
        id=name_tag.id,
        booking_id=name_tag.booking_id,
        first_name=name_tag.first_name,
        last_name=name_tag.last_name,
        position=name_tag.position,
    )


class NametagsMixin(KpServiceBase):
    def _ensure_nametags_editable(self, booking: KpEventBooking, context: str) -> None:
        self._ensure_active_booking(booking, context)
        if booking.event.is_nametags_deadline_passed():
            raise KpNametagsDeadlinePassed(
                f"{context}:deadline_passed:{booking.id}:"
                f"{booking.event.nametags_deadline}"
            )

    async def _booking_name_tags(self, booking_id: UUID) -> list[NameTagResult]:
        name_tags = await self.kp_repository.list_name_tags_for_booking(booking_id)
        return [name_tag_result(name_tag) for name_tag in name_tags]

    async def list_booking_name_tags(self, booking_id: UUID) -> list[NameTagResult]:
        company_user = require_assigned_company_user(self.current_user)
        booking = await self._get_owned_booking(
            booking_id, company_user.company_id, "list_booking_name_tags"
        )
        return await self._booking_name_tags(booking.id)

    async def list_booking_name_tags_for_staff(
        self, booking_id: UUID
    ) -> list[NameTagResult]:
        require_staff_user(self.current_user)
        booking = await self._get_booking(booking_id)
        return await self._booking_name_tags(booking.id)

    async def replace_booking_name_tags(
        self, booking_id: UUID, name_tags: Sequence[NameTagInput]
    ) -> list[NameTagResult]:
        company_user = require_assigned_company_user(self.current_user)
        booking = await self._get_owned_booking(
            booking_id, company_user.company_id, "replace_booking_name_tags"
        )
        self._ensure_nametags_editable(booking, "replace_booking_name_tags")
        maximum = booking.event.max_nametags_per_booking
        if len(name_tags) > maximum:
            raise KpNametagLimitReached(
                f"replace_booking_name_tags:limit_reached:{booking.id}:{maximum}"
            )
        replaced = await self.kp_repository.replace_name_tags(booking, name_tags)
        return [name_tag_result(name_tag) for name_tag in replaced]
