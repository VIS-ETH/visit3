from uuid import UUID

from fastapi import APIRouter, File, Request, UploadFile

from app.core.config import get_settings
from app.core.deps import BookletServiceDep, EventBannerServiceDep
from app.core.rate_limit import user_rate_limit
from app.core.uploads import upload_size
from app.schemas.company import (
    BookletBackgroundResponse,
    BookletBackgroundResult,
    BookletPageResponse,
    BookletPageResult,
)
from app.schemas.kp import EventBannerResponse, EventBannerResult

router = APIRouter()


BOOKLET_SAMPLE_RATE_LIMIT = user_rate_limit(
    "booklet_sample",
    get_settings().BOOKLET_PAGE_RATE_LIMIT_MAX_REQUESTS,
    get_settings().BOOKLET_PAGE_RATE_LIMIT_WINDOW_SECONDS,
)


@router.get(
    "/events/{event_id}/banner",
    operation_id="getEventBanner",
    response_model=EventBannerResponse | None,
)
async def get_event_banner(
    event_banner_service: EventBannerServiceDep, event_id: UUID
) -> EventBannerResult | None:
    return await event_banner_service.get_banner(event_id)


@router.put(
    "/events/{event_id}/banner",
    operation_id="uploadEventBanner",
    response_model=EventBannerResponse,
)
async def upload_event_banner(
    event_banner_service: EventBannerServiceDep,
    request: Request,
    event_id: UUID,
    file: UploadFile = File(...),
) -> EventBannerResult:
    return await event_banner_service.upload_banner(
        event_id=event_id,
        upload=file,
        content_length=upload_size(request, file),
        content_type=file.content_type,
    )


@router.delete("/events/{event_id}/banner", operation_id="resetEventBanner")
async def reset_event_banner(
    event_banner_service: EventBannerServiceDep, event_id: UUID
) -> None:
    await event_banner_service.reset_banner(event_id)


@router.get(
    "/events/{event_id}/booklet/background",
    operation_id="getBookletBackground",
    response_model=BookletBackgroundResponse | None,
)
async def get_booklet_background(
    booklet_service: BookletServiceDep, event_id: UUID
) -> BookletBackgroundResult | None:
    return await booklet_service.get_booklet_background(event_id)


@router.put(
    "/events/{event_id}/booklet/background",
    operation_id="uploadBookletBackground",
    response_model=BookletBackgroundResponse,
)
async def upload_booklet_background(
    booklet_service: BookletServiceDep,
    request: Request,
    event_id: UUID,
    file: UploadFile = File(...),
) -> BookletBackgroundResult:
    return await booklet_service.upload_booklet_background(
        event_id=event_id,
        filename=file.filename or "booklet-background.pdf",
        upload=file,
        content_length=upload_size(request, file),
    )


@router.delete(
    "/events/{event_id}/booklet/background",
    operation_id="resetBookletBackground",
)
async def reset_booklet_background(
    booklet_service: BookletServiceDep, event_id: UUID
) -> None:
    await booklet_service.reset_booklet_background(event_id)


@router.post(
    "/events/{event_id}/booklet/preview",
    operation_id="previewBookletSample",
    response_model=BookletPageResponse,
    dependencies=[BOOKLET_SAMPLE_RATE_LIMIT],
)
async def preview_booklet_sample(
    booklet_service: BookletServiceDep, event_id: UUID
) -> BookletPageResult:
    return await booklet_service.preview_booklet_sample(event_id)
