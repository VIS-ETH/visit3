from collections.abc import Sequence
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import selectinload
from sqlmodel import col, select

from app.models.kp_event import (
    KpEventBoothZoneServiceLink,
    KpEventService,
    KpEventServiceExclusion,
    KpEventServiceInclusion,
    KpEventServiceRequirement,
    KpServiceCategory,
)
from app.repositories.base import rel
from app.repositories.kp_repository.base import KpRepositoryBase
from app.schemas.kp import (
    CreateServiceInput,
    IncludedServiceInput,
    ServiceRequirementInput,
    UpdateServiceInput,
)

SERVICE_RELATION_FIELDS = {"requirements", "included_services", "excluded_service_ids"}


def _service_options() -> tuple[Any, ...]:
    return (
        selectinload(rel(KpEventService.requirements)),
        selectinload(rel(KpEventService.image_stored_file)),
        selectinload(rel(KpEventService.included_services)),
        selectinload(rel(KpEventService.excluded_services)),
    )


class ServicesMixin(KpRepositoryBase):
    async def list_services(
        self, event_id: UUID, category: KpServiceCategory | None = None
    ) -> Sequence[KpEventService]:
        statement = (
            select(KpEventService)
            .where(col(KpEventService.event_id) == event_id)
            .order_by(col(KpEventService.order).asc(), col(KpEventService.name).asc())
            .options(*_service_options())
        )
        if category is not None:
            statement = statement.where(col(KpEventService.category) == category)
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_service_by_id(self, service_id: UUID) -> Optional[KpEventService]:
        statement = (
            select(KpEventService)
            .where(col(KpEventService.id) == service_id)
            .options(*_service_options())
            .execution_options(populate_existing=True)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_service_by_name(
        self, event_id: UUID, name: str
    ) -> Optional[KpEventService]:
        statement = (
            select(KpEventService)
            .where(
                col(KpEventService.event_id) == event_id,
                col(KpEventService.name) == name,
            )
            .options(*_service_options())
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def create_service(
        self, event_id: UUID, create_service_input: CreateServiceInput
    ) -> KpEventService:
        async with self.committing():
            service = KpEventService(
                **create_service_input.model_dump(exclude=SERVICE_RELATION_FIELDS),
                event_id=event_id,
            )
            self._validate_model(service)
            self.session.add(service)
            await self.session.flush()
            await self._replace_service_requirements(
                service, create_service_input.requirements
            )
            await self._replace_service_relations(
                service,
                create_service_input.included_services,
                create_service_input.excluded_service_ids,
            )
        return await self.get_service_by_id(service.id) or service

    async def update_service(
        self, service: KpEventService, update_service_input: UpdateServiceInput
    ) -> KpEventService:
        async with self.committing():
            service.sqlmodel_update(
                update_service_input.model_dump(
                    exclude_unset=True, exclude=SERVICE_RELATION_FIELDS
                )
            )
            self._validate_model(service)
            self.session.add(service)
            if update_service_input.requirements is not None:
                await self._replace_service_requirements(
                    service, update_service_input.requirements
                )
            await self._replace_service_relations(
                service,
                update_service_input.included_services,
                update_service_input.excluded_service_ids,
            )
        return await self.get_service_by_id(service.id) or service

    async def _replace_service_requirements(
        self,
        service: KpEventService,
        requirements: list[ServiceRequirementInput],
    ) -> None:
        statement = select(KpEventServiceRequirement).where(
            col(KpEventServiceRequirement.service_id) == service.id
        )
        result = await self.session.execute(statement)
        existing_requirements = result.scalars().all()
        existing_by_id = {
            requirement.id: requirement for requirement in existing_requirements
        }
        kept_ids: set[UUID] = set()

        for requirement_input in requirements:
            requirement = (
                existing_by_id.get(requirement_input.id)
                if requirement_input.id is not None
                else None
            )
            data = requirement_input.model_dump(exclude={"id"})
            if requirement is None:
                requirement = KpEventServiceRequirement(service_id=service.id, **data)
            else:
                kept_ids.add(requirement.id)
                requirement.sqlmodel_update(data)

            self._validate_model(requirement)
            self.session.add(requirement)

        for requirement in existing_requirements:
            if requirement.id not in kept_ids:
                self.delete(requirement)

    async def _replace_service_relations(
        self,
        service: KpEventService,
        included_services: Sequence[IncludedServiceInput] | None,
        excluded_service_ids: Sequence[UUID] | None,
    ) -> None:
        if included_services is not None:
            await self._replace_service_inclusions(service, included_services)
        if excluded_service_ids is not None:
            await self._replace_service_exclusions(service, excluded_service_ids)

    async def _replace_service_inclusions(
        self,
        service: KpEventService,
        included_services: Sequence[IncludedServiceInput],
    ) -> None:
        result = await self.session.execute(
            select(KpEventServiceInclusion).where(
                col(KpEventServiceInclusion.service_id) == service.id
            )
        )
        removed = {
            inclusion.included_service_id: inclusion
            for inclusion in result.scalars().all()
        }
        for included_service in included_services:
            inclusion = removed.pop(
                included_service.service_id, None
            ) or KpEventServiceInclusion(
                service_id=service.id,
                included_service_id=included_service.service_id,
            )
            inclusion.included_quantity = included_service.included_quantity
            self._validate_model(inclusion)
            self.session.add(inclusion)
        for inclusion in removed.values():
            await self.session.delete(inclusion)

    async def _replace_service_exclusions(
        self, service: KpEventService, excluded_service_ids: Sequence[UUID]
    ) -> None:
        result = await self.session.execute(
            select(KpEventServiceExclusion).where(
                (col(KpEventServiceExclusion.service_id) == service.id)
                | (col(KpEventServiceExclusion.excluded_service_id) == service.id)
            )
        )
        existing = {
            (exclusion.service_id, exclusion.excluded_service_id): exclusion
            for exclusion in result.scalars().all()
        }
        for excluded_service_id in excluded_service_ids:
            for pair in (
                (service.id, excluded_service_id),
                (excluded_service_id, service.id),
            ):
                if existing.pop(pair, None) is None:
                    self.session.add(
                        KpEventServiceExclusion(
                            service_id=pair[0], excluded_service_id=pair[1]
                        )
                    )
        for exclusion in existing.values():
            await self.session.delete(exclusion)

    async def set_service_image_stored_file_id(
        self, service: KpEventService, stored_file_id: UUID | None
    ) -> KpEventService:
        async with self.committing():
            service.image_stored_file_id = stored_file_id
            self.session.add(service)
        return await self.get_service_by_id(service.id) or service

    async def delete_service(self, service: KpEventService) -> None:
        async with self.committing():
            await self.hard_delete_where(
                KpEventBoothZoneServiceLink,
                col(KpEventBoothZoneServiceLink.service_id) == service.id,
            )
            await self.hard_delete_where(
                KpEventServiceInclusion,
                (col(KpEventServiceInclusion.service_id) == service.id)
                | (col(KpEventServiceInclusion.included_service_id) == service.id),
            )
            await self.hard_delete_where(
                KpEventServiceExclusion,
                (col(KpEventServiceExclusion.service_id) == service.id)
                | (col(KpEventServiceExclusion.excluded_service_id) == service.id),
            )
            await self.delete_where(
                KpEventServiceRequirement,
                col(KpEventServiceRequirement.service_id) == service.id,
            )
            service.image_stored_file_id = None
            self.delete(service)
