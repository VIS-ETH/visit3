from uuid import UUID

from fastapi import APIRouter, File, Request, UploadFile

from app.core.deps import KpServiceDep
from app.core.uploads import upload_size
from app.schemas.kp import CreateServiceRequest, ServiceResponse, UpdateServiceRequest

router = APIRouter()


@router.get(
    "/events/{event_id}/services",
    operation_id="listServices",
    response_model=list[ServiceResponse],
)
async def list_services(
    kp_service: KpServiceDep, event_id: UUID
) -> list[ServiceResponse]:
    return await kp_service.list_services(event_id)


@router.post(
    "/events/{event_id}/services",
    operation_id="createService",
    response_model=ServiceResponse,
)
async def create_service(
    kp_service: KpServiceDep, event_id: UUID, request: CreateServiceRequest
) -> ServiceResponse:
    return await kp_service.create_service(event_id, request)


@router.patch(
    "/services/{service_id}",
    operation_id="updateService",
    response_model=ServiceResponse,
)
async def update_service(
    kp_service: KpServiceDep,
    service_id: UUID,
    request: UpdateServiceRequest,
) -> ServiceResponse:
    return await kp_service.update_service(service_id, request)


@router.delete("/services/{service_id}", operation_id="deleteService")
async def delete_service(kp_service: KpServiceDep, service_id: UUID) -> None:
    await kp_service.delete_service(service_id)


@router.post(
    "/services/{service_id}/image",
    operation_id="uploadServiceImage",
    response_model=ServiceResponse,
)
async def upload_service_image(
    kp_service: KpServiceDep,
    request: Request,
    service_id: UUID,
    file: UploadFile = File(...),
) -> ServiceResponse:
    return await kp_service.upload_service_image(
        service_id=service_id,
        filename=file.filename or "service-image",
        upload=file,
        content_length=upload_size(request, file),
        content_type=file.content_type,
    )


@router.delete(
    "/services/{service_id}/image",
    operation_id="deleteServiceImage",
    response_model=ServiceResponse,
)
async def delete_service_image(
    kp_service: KpServiceDep,
    service_id: UUID,
) -> ServiceResponse:
    return await kp_service.delete_service_image(service_id)
