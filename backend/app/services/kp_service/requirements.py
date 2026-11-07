from uuid import UUID

from app.core.auth_context import require_assigned_company_user, require_staff_user
from app.core.exceptions import (
    KpBookingNotFound,
    KpRequirementBookingServiceMismatch,
    KpRequirementFileUploadNotAllowed,
    KpRequirementTextAnswerNotAllowed,
    KpServiceRequirementNotFound,
)
from app.models.kp_event import (
    KpEventBookingService,
    KpEventBookingServiceFileLink,
    KpEventServiceRequirement,
    KpEventServiceRequirementType,
)
from app.schemas.kp import (
    BookingRequirementFileMapResponse,
    RequirementFileResponse,
    RequirementTextResponse,
    StoredFileResponse,
)
from app.services.kp_service.base import KpServiceBase
from app.services.storage_service import UploadKind, UploadStream

REQUIREMENT_UPLOAD_KINDS = {
    KpEventServiceRequirementType.IMAGE: UploadKind.IMAGE,
    KpEventServiceRequirementType.PDF: UploadKind.PDF,
    KpEventServiceRequirementType.VIDEO: UploadKind.VIDEO,
}


def requirement_text_response(
    answer: KpEventBookingServiceFileLink,
) -> RequirementTextResponse:
    return RequirementTextResponse(
        id=answer.id,
        booking_service_id=answer.booking_service_id,
        requirement_id=answer.requirement_id,
        text_value=answer.text_value or "",
    )


class RequirementsMixin(KpServiceBase):
    async def _get_requirement_for_booking_service(
        self, booking_service: KpEventBookingService, requirement_id: UUID
    ) -> KpEventServiceRequirement:
        requirement = await self.kp_repository.get_service_requirement_by_id(
            requirement_id
        )
        if requirement is None:
            raise KpServiceRequirementNotFound(
                f"booking_requirement:not_found:{requirement_id}"
            )

        if requirement.service_id != booking_service.service_id:
            raise KpRequirementBookingServiceMismatch(
                f"booking_requirement:service_mismatch:{booking_service.id}:{requirement_id}"
            )
        return requirement

    async def _get_text_requirement(
        self, booking_service: KpEventBookingService, requirement_id: UUID
    ) -> KpEventServiceRequirement:
        requirement = await self._get_requirement_for_booking_service(
            booking_service, requirement_id
        )
        if requirement.type != KpEventServiceRequirementType.TEXT:
            raise KpRequirementTextAnswerNotAllowed(
                f"booking_requirement:not_text:{requirement.id}"
            )
        return requirement

    def _requirement_upload_kind(
        self, requirement: KpEventServiceRequirement
    ) -> UploadKind:
        if requirement.type == KpEventServiceRequirementType.TEXT:
            raise KpRequirementFileUploadNotAllowed(
                f"booking_requirement:not_file_upload:{requirement.id}"
            )
        return REQUIREMENT_UPLOAD_KINDS.get(requirement.type, UploadKind.FILE)

    def _validate_requirement_upload(
        self,
        kind: UploadKind,
        filename: str,
        content: bytes,
        content_type: str | None,
        *,
        error_context: str,
    ) -> str:
        validate = {
            UploadKind.IMAGE: self.storage_service.validate_image_file,
            UploadKind.PDF: self.storage_service.validate_pdf_file,
            UploadKind.VIDEO: self.storage_service.validate_video_file,
        }.get(kind, self.storage_service.validate_generic_file)
        return validate(filename, content, content_type, error_context=error_context)

    async def upload_booking_requirement_file(
        self,
        booking_service_id: UUID,
        requirement_id: UUID,
        filename: str,
        upload: UploadStream,
        content_length: int | None = None,
        content_type: str | None = None,
    ) -> KpEventBookingServiceFileLink:
        company_user = require_assigned_company_user(self.current_user)
        booking_service = await self._get_owned_booking_service(
            booking_service_id, company_user.company_id
        )
        self._ensure_booking_editable_by_company(
            booking_service.booking, "upload_booking_requirement_file"
        )
        requirement = await self._get_requirement_for_booking_service(
            booking_service, requirement_id
        )
        kind = self._requirement_upload_kind(requirement)
        error_context = f"booking_requirement:{requirement.type.value}:{requirement.id}"
        content = await self.storage_service.read_upload(
            upload,
            content_length=content_length,
            kind=kind,
            error_context=error_context,
        )
        mime_type = self._validate_requirement_upload(
            kind, filename, content, content_type, error_context=error_context
        )
        existing_file = await self.kp_repository.get_requirement_file(
            booking_service.id, requirement.id
        )
        old_stored_file = existing_file.stored_file if existing_file else None
        requirement_file = await self.stored_files.save(
            f"kp/booking-services/{booking_service.id}/requirements/{requirement.id}",
            filename,
            content,
            mime_type,
            lambda stored_file: self.kp_repository.upsert_requirement_file_link(
                booking_service_id=booking_service.id,
                requirement_id=requirement.id,
                stored_file_id=stored_file.id,
            ),
        )
        await self.stored_files.discard(old_stored_file)
        return requirement_file

    async def _stored_requirement_file(
        self, booking_service: KpEventBookingService, requirement_id: UUID
    ) -> KpEventBookingServiceFileLink | None:
        await self._get_requirement_for_booking_service(booking_service, requirement_id)
        requirement_file = await self.kp_repository.get_requirement_file(
            booking_service.id, requirement_id
        )
        if requirement_file is None or requirement_file.stored_file is None:
            return None
        return requirement_file

    async def _requirement_file_download_url(
        self, requirement_file: KpEventBookingServiceFileLink | None, context: str
    ) -> str:
        if requirement_file is None or requirement_file.stored_file is None:
            raise KpServiceRequirementNotFound(context)
        return await self.storage_service.generate_download_url(
            requirement_file.stored_file.storage_key,
            requirement_file.stored_file.original_filename,
        )

    async def get_booking_requirement_file(
        self, booking_service_id: UUID, requirement_id: UUID
    ) -> KpEventBookingServiceFileLink | None:
        company_user = require_assigned_company_user(self.current_user)
        booking_service = await self._get_owned_booking_service(
            booking_service_id, company_user.company_id
        )
        return await self._stored_requirement_file(booking_service, requirement_id)

    async def get_booking_requirement_file_download_url(
        self, booking_service_id: UUID, requirement_id: UUID
    ) -> str:
        return await self._requirement_file_download_url(
            await self.get_booking_requirement_file(booking_service_id, requirement_id),
            f"booking_requirement_file:not_found:{booking_service_id}:{requirement_id}",
        )

    async def get_staff_booking_requirement_file(
        self, booking_service_id: UUID, requirement_id: UUID
    ) -> KpEventBookingServiceFileLink | None:
        require_staff_user(self.current_user)
        booking_service = await self._get_booking_service(booking_service_id)
        return await self._stored_requirement_file(booking_service, requirement_id)

    async def get_staff_booking_requirement_file_download_url(
        self, booking_service_id: UUID, requirement_id: UUID
    ) -> str:
        return await self._requirement_file_download_url(
            await self.get_staff_booking_requirement_file(
                booking_service_id, requirement_id
            ),
            f"staff_booking_requirement_file:not_found:{booking_service_id}:{requirement_id}",
        )

    async def get_booking_requirement_text(
        self, booking_service_id: UUID, requirement_id: UUID
    ) -> RequirementTextResponse | None:
        company_user = require_assigned_company_user(self.current_user)
        booking_service = await self._get_owned_booking_service(
            booking_service_id, company_user.company_id
        )
        requirement = await self._get_text_requirement(booking_service, requirement_id)
        requirement_answer = await self.kp_repository.get_requirement_file(
            booking_service.id, requirement.id
        )
        if requirement_answer is None or requirement_answer.text_value is None:
            return None
        return requirement_text_response(requirement_answer)

    async def upsert_booking_requirement_text(
        self, booking_service_id: UUID, requirement_id: UUID, text_value: str
    ) -> RequirementTextResponse:
        company_user = require_assigned_company_user(self.current_user)
        booking_service = await self._get_owned_booking_service(
            booking_service_id, company_user.company_id
        )
        self._ensure_booking_editable_by_company(
            booking_service.booking, "upsert_booking_requirement_text"
        )
        requirement = await self._get_text_requirement(booking_service, requirement_id)
        old_answer = await self.kp_repository.get_requirement_file(
            booking_service.id, requirement.id
        )
        old_stored_file = old_answer.stored_file if old_answer is not None else None
        requirement_answer = await self.kp_repository.upsert_requirement_text_answer(
            booking_service_id=booking_service.id,
            requirement_id=requirement.id,
            text_value=text_value.strip(),
        )
        await self.stored_files.discard(old_stored_file)
        return requirement_text_response(requirement_answer)

    async def delete_booking_requirement_answer(
        self, booking_service_id: UUID, requirement_id: UUID
    ) -> None:
        company_user = require_assigned_company_user(self.current_user)
        booking_service = await self._get_owned_booking_service(
            booking_service_id, company_user.company_id
        )
        self._ensure_booking_editable_by_company(
            booking_service.booking, "delete_booking_requirement_answer"
        )
        await self._get_requirement_for_booking_service(booking_service, requirement_id)
        answer = await self.kp_repository.get_requirement_file(
            booking_service.id, requirement_id
        )
        if answer is None:
            return
        stored_file = answer.stored_file
        await self.kp_repository.delete_requirement_file_link(answer)
        await self.stored_files.discard(stored_file)

    async def list_staff_booking_requirement_files(
        self, event_id: UUID, booking_id: UUID
    ) -> BookingRequirementFileMapResponse:
        require_staff_user(self.current_user)
        await self._get_event(event_id)
        booking = await self._get_booking(booking_id)
        if booking.event_id != event_id:
            raise KpBookingNotFound(
                f"staff_booking_requirement_files:event_mismatch:{event_id}:{booking_id}"
            )

        files: dict[UUID, RequirementFileResponse] = {}
        for booking_service in booking.services:
            for requirement_file in booking_service.requirement_file_links:
                if requirement_file.stored_file is None:
                    continue
                files[requirement_file.requirement_id] = RequirementFileResponse(
                    id=requirement_file.id,
                    booking_service_id=requirement_file.booking_service_id,
                    requirement_id=requirement_file.requirement_id,
                    stored_file=StoredFileResponse.model_validate(
                        requirement_file.stored_file, from_attributes=True
                    ),
                )
        return BookingRequirementFileMapResponse(files=files)
