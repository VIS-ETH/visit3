from typing import Optional
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from sqlmodel import col, select

from app.core.exceptions import ConcurrentChange
from app.models.kp_event import KpEventBookingServiceFileLink, KpEventServiceRequirement
from app.repositories.base import rel
from app.repositories.kp_repository.base import KpRepositoryBase


class RequirementsMixin(KpRepositoryBase):
    async def get_service_requirement_by_id(
        self, requirement_id: UUID
    ) -> Optional[KpEventServiceRequirement]:
        statement = (
            select(KpEventServiceRequirement)
            .where(col(KpEventServiceRequirement.id) == requirement_id)
            .options(selectinload(rel(KpEventServiceRequirement.service)))
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_requirement_file(
        self, booking_service_id: UUID, requirement_id: UUID
    ) -> Optional[KpEventBookingServiceFileLink]:
        statement = (
            select(KpEventBookingServiceFileLink)
            .where(
                col(KpEventBookingServiceFileLink.booking_service_id)
                == booking_service_id,
                col(KpEventBookingServiceFileLink.requirement_id) == requirement_id,
            )
            .options(
                selectinload(rel(KpEventBookingServiceFileLink.requirement)),
                selectinload(rel(KpEventBookingServiceFileLink.stored_file)),
                selectinload(rel(KpEventBookingServiceFileLink.booking_service)),
            )
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def _stored_answer(
        self, booking_service_id: UUID, requirement_id: UUID
    ) -> Optional[KpEventBookingServiceFileLink]:
        statement = select(KpEventBookingServiceFileLink).where(
            col(KpEventBookingServiceFileLink.booking_service_id) == booking_service_id,
            col(KpEventBookingServiceFileLink.requirement_id) == requirement_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def _write_answer(
        self,
        answer: Optional[KpEventBookingServiceFileLink],
        booking_service_id: UUID,
        requirement_id: UUID,
        stored_file_id: UUID | None,
        text_value: str | None,
    ) -> None:
        async with self.committing():
            if answer is None:
                answer = KpEventBookingServiceFileLink(
                    booking_service_id=booking_service_id,
                    requirement_id=requirement_id,
                )
            answer.stored_file_id = stored_file_id
            answer.text_value = text_value
            self._validate_model(answer)
            self.session.add(answer)

    async def _save_answer(
        self,
        booking_service_id: UUID,
        requirement_id: UUID,
        stored_file_id: UUID | None,
        text_value: str | None,
    ) -> KpEventBookingServiceFileLink:
        answer = await self.get_requirement_file(booking_service_id, requirement_id)
        try:
            await self._write_answer(
                answer, booking_service_id, requirement_id, stored_file_id, text_value
            )
        except IntegrityError:
            await self._write_answer(
                await self._stored_answer(booking_service_id, requirement_id),
                booking_service_id,
                requirement_id,
                stored_file_id,
                text_value,
            )
        saved = await self._stored_answer(booking_service_id, requirement_id)
        if saved is None:
            raise ConcurrentChange(
                f"requirement_answer:{booking_service_id}:{requirement_id}"
            )
        await self.session.refresh(saved)
        return (
            await self.get_requirement_file(booking_service_id, requirement_id) or saved
        )

    async def upsert_requirement_file_link(
        self,
        booking_service_id: UUID,
        requirement_id: UUID,
        stored_file_id: UUID,
    ) -> KpEventBookingServiceFileLink:
        return await self._save_answer(
            booking_service_id, requirement_id, stored_file_id, None
        )

    async def upsert_requirement_text_answer(
        self,
        booking_service_id: UUID,
        requirement_id: UUID,
        text_value: str,
    ) -> KpEventBookingServiceFileLink:
        return await self._save_answer(
            booking_service_id, requirement_id, None, text_value
        )

    async def delete_requirement_file_link(
        self, requirement_file: KpEventBookingServiceFileLink
    ) -> None:
        async with self.committing():
            await self.session.delete(requirement_file)
