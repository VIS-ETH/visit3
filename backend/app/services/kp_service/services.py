from collections.abc import Sequence
from uuid import UUID

from app.core.auth_context import (
    require_confirmed_company_user,
    require_kp_president_user,
)
from app.core.exceptions import (
    KpIncludedExceedsMax,
    KpIncludedServiceDuplicate,
    KpServiceInUse,
    KpServiceNameExists,
    KpServiceNotFound,
    KpServiceRelationInvalid,
)
from app.models.kp_event import (
    UNLIMITED_TOTAL_QUANTITY,
    KpEvent,
    KpEventService,
    KpServiceCategory,
)
from app.schemas.kp import (
    CreateServiceInput,
    IncludedServiceInput,
    ServiceResponse,
    UpdateServiceInput,
)
from app.services.kp_service.responses import ResponsesMixin
from app.services.storage_service import UploadKind, UploadStream


class ServicesMixin(ResponsesMixin):
    async def _get_service(self, service_id: UUID) -> KpEventService:
        service = await self.kp_repository.get_service_by_id(service_id)
        if service is None:
            raise KpServiceNotFound(f"service:not_found:{service_id}")
        return service

    async def _remaining_total_quantity(self, service: KpEventService) -> int | None:
        if service.max_total_quantity == UNLIMITED_TOTAL_QUANTITY:
            return None
        charged = await self.kp_repository.count_active_charged_service_quantity(
            service.id
        )
        return max(service.max_total_quantity - charged, 0)

    async def list_services(self, event_id: UUID) -> list[ServiceResponse]:
        require_kp_president_user(self.current_user)
        await self._get_event(event_id)
        services = await self.kp_repository.list_services(event_id)
        return [await self._build_service_response(service) for service in services]

    async def list_available_services_for_company(
        self, event_id: UUID, category: KpServiceCategory | None = None
    ) -> list[ServiceResponse]:
        require_confirmed_company_user(self.current_user)
        await self._get_event(event_id)
        services = await self.kp_repository.list_services(event_id, category)
        return [
            await self._build_service_response(
                service, await self._remaining_total_quantity(service)
            )
            for service in services
            if service.is_active
        ]

    async def _ensure_service_name_free(
        self,
        event_id: UUID,
        context: str,
        name: str | None,
        current_id: UUID | None = None,
    ) -> None:
        if name is None:
            return
        existing = await self.kp_repository.get_service_by_name(event_id, name)
        if existing is not None and existing.id != current_id:
            raise KpServiceNameExists(f"{context}:{event_id}:{name}")

    async def create_service(
        self, event_id: UUID, create_service_input: CreateServiceInput
    ) -> ServiceResponse:
        require_kp_president_user(self.current_user)
        await self._get_event(event_id)
        await self._ensure_service_name_free(
            event_id, "create_service", create_service_input.name
        )
        await self._ensure_service_relations_valid(
            event_id,
            None,
            create_service_input.included_services,
            create_service_input.excluded_service_ids,
            "create_service",
        )
        service = await self.kp_repository.create_service(
            event_id, create_service_input
        )
        return await self._build_service_response(service)

    async def update_service(
        self, service_id: UUID, update_service_input: UpdateServiceInput
    ) -> ServiceResponse:
        require_kp_president_user(self.current_user)
        service = await self._get_service(service_id)
        new_name = update_service_input.model_dump(exclude_unset=True).get("name")
        await self._ensure_service_name_free(
            service.event_id,
            "update_service",
            new_name if new_name != service.name else None,
            service.id,
        )
        await self._ensure_max_quantity_covers_inclusions(
            service, update_service_input.max_quantity_per_booking
        )
        await self._ensure_service_relations_valid(
            service.event_id,
            service,
            update_service_input.included_services,
            update_service_input.excluded_service_ids,
            "update_service",
        )
        updated = await self.kp_repository.update_service(service, update_service_input)
        return await self._build_service_response(updated)

    async def _ensure_service_relations_valid(
        self,
        event_id: UUID,
        service: KpEventService | None,
        included_services: Sequence[IncludedServiceInput] | None,
        excluded_service_ids: Sequence[UUID] | None,
        context: str,
    ) -> None:
        service_id = service.id if service is not None else None
        included_ids: set[UUID] = set()
        excluded_ids: set[UUID] = set()
        if included_services is None:
            included_ids = (
                {
                    inclusion.included_service_id
                    for inclusion in service.included_services
                }
                if service is not None
                else set[UUID]()
            )
        else:
            for included_service in included_services:
                related_id = included_service.service_id
                if related_id in included_ids:
                    raise KpIncludedServiceDuplicate(
                        f"{context}:duplicate:{related_id}"
                    )
                included_ids.add(related_id)
                if related_id == service_id:
                    raise KpServiceRelationInvalid(f"{context}:self:{related_id}")
                related = await self._related_service(event_id, related_id, context)
                if related.included_services:
                    raise KpServiceRelationInvalid(f"{context}:nested:{related_id}")
                if (
                    included_service.included_quantity
                    > related.max_quantity_per_booking
                ):
                    raise KpIncludedExceedsMax(
                        f"{context}:included_exceeds_max:{related_id}:"
                        f"{included_service.included_quantity}"
                    )
            if included_ids and service_id is not None:
                if await self.kp_repository.list_containing_services(service_id):
                    raise KpServiceRelationInvalid(f"{context}:nested:{service_id}")
        if excluded_service_ids is None:
            excluded_ids = (
                {
                    exclusion.excluded_service_id
                    for exclusion in service.excluded_services
                }
                if service is not None
                else set[UUID]()
            )
        else:
            excluded_ids = set(excluded_service_ids)
            for related_id in excluded_ids:
                if related_id == service_id:
                    raise KpServiceRelationInvalid(f"{context}:self:{related_id}")
                await self._related_service(event_id, related_id, context)
        if included_ids & excluded_ids:
            raise KpServiceRelationInvalid(f"{context}:included_and_excluded")
        if excluded_service_ids is not None and service_id is not None:
            for containing in await self.kp_repository.list_containing_services(
                service_id
            ):
                package_ids = {containing.service_id} | {
                    inclusion.included_service_id
                    for inclusion in await self.kp_repository.list_service_inclusions(
                        [containing.service_id]
                    )
                }
                if package_ids & excluded_ids:
                    raise KpServiceRelationInvalid(
                        f"{context}:contents_excluded:{containing.service_id}"
                    )
        for exclusion in await self.kp_repository.list_service_exclusions(
            list(included_ids)
        ):
            if exclusion.excluded_service_id in included_ids or (
                service_id is not None and exclusion.excluded_service_id == service_id
            ):
                raise KpServiceRelationInvalid(
                    f"{context}:contents_excluded:{exclusion.service_id}"
                )

    async def _ensure_max_quantity_covers_inclusions(
        self, service: KpEventService, max_quantity_per_booking: int | None
    ) -> None:
        if max_quantity_per_booking is None:
            return
        included_quantity = await self.kp_repository.max_included_quantity(service.id)
        if included_quantity > max_quantity_per_booking:
            raise KpIncludedExceedsMax(
                f"update_service:included_exceeds_max:{service.id}:{included_quantity}"
            )

    async def delete_service(self, service_id: UUID) -> None:
        require_kp_president_user(self.current_user)
        service = await self._get_service(service_id)
        await self.kp_repository.lock_model_by_id(KpEvent, service.event_id)
        active_bookings = await self.kp_repository.count_active_bookings_with_service(
            service_id
        )
        if active_bookings > 0:
            raise KpServiceInUse(
                f"delete_service:in_use:{service_id}:{active_bookings}"
            )
        await self.kp_repository.delete_service(service)

    async def upload_service_image(
        self,
        service_id: UUID,
        filename: str,
        upload: UploadStream,
        content_length: int | None,
        content_type: str | None,
    ) -> ServiceResponse:
        require_kp_president_user(self.current_user)
        service = await self._get_service(service_id)
        error_context = f"service_image:{service_id}"
        content = await self.storage_service.read_upload(
            upload,
            content_length=content_length,
            kind=UploadKind.IMAGE,
            error_context=error_context,
        )
        mime_type = self.storage_service.validate_image_file(
            filename,
            content,
            content_type,
            error_context=error_context,
        )
        old_stored_file = service.image_stored_file
        updated = await self.stored_files.save(
            f"kp/services/{service_id}/image",
            filename,
            content,
            mime_type,
            lambda stored_file: self.kp_repository.set_service_image_stored_file_id(
                service, stored_file.id
            ),
        )
        await self.stored_files.discard(old_stored_file)
        return await self._build_service_response(updated)

    async def delete_service_image(self, service_id: UUID) -> ServiceResponse:
        require_kp_president_user(self.current_user)
        service = await self._get_service(service_id)
        stored_file = service.image_stored_file
        if stored_file is None:
            return await self._build_service_response(service)
        updated = await self.kp_repository.set_service_image_stored_file_id(
            service, None
        )
        await self.stored_files.discard(stored_file)
        return await self._build_service_response(updated)
