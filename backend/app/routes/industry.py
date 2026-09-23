from collections.abc import Sequence
from uuid import UUID

from fastapi import APIRouter

from app.core.deps import CsrfDep, IndustryServiceDep
from app.models.industry import Industry
from app.schemas.industry import (
    CreateIndustryRequest,
    IndustryResponse,
    UpdateIndustryRequest,
)

router = APIRouter(prefix="/industries", tags=["industry"], dependencies=[CsrfDep])


@router.get(
    "", operation_id="listIndustryCatalogue", response_model=list[IndustryResponse]
)
async def list_industry_catalogue(
    industry_service: IndustryServiceDep,
) -> Sequence[Industry]:
    return await industry_service.list_industries()


@router.post(
    "", operation_id="createIndustryCatalogueEntry", response_model=IndustryResponse
)
async def create_industry_catalogue_entry(
    industry_service: IndustryServiceDep,
    request: CreateIndustryRequest,
) -> Industry:
    return await industry_service.create_industry(request.name)


@router.patch(
    "/{industry_id}",
    operation_id="updateIndustryCatalogueEntry",
    response_model=IndustryResponse,
)
async def update_industry_catalogue_entry(
    industry_service: IndustryServiceDep,
    industry_id: UUID,
    request: UpdateIndustryRequest,
) -> Industry:
    return await industry_service.update_industry(industry_id, request.name)


@router.delete("/{industry_id}", operation_id="deleteIndustryCatalogueEntry")
async def delete_industry_catalogue_entry(
    industry_service: IndustryServiceDep,
    industry_id: UUID,
) -> None:
    await industry_service.delete_industry(industry_id)
