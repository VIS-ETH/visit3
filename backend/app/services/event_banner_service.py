import asyncio
import logging
from dataclasses import dataclass
from io import BytesIO
from uuid import UUID, uuid4

from PIL import Image, ImageOps

from app.core.auth_context import require_kp_president_user
from app.core.exceptions import (
    EventBannerTooSmall,
    KpEventNotFound,
    StorageDeleteFailed,
    StorageFileTooLarge,
)
from app.models.kp_event import KpEvent, KpEventBanner
from app.models.storage import StoredFile
from app.models.user import User
from app.repositories.kp_repository import KpRepository
from app.schemas.kp import EventBannerResult, EventBannerSource, KpLatestResult
from app.services.storage_service import (
    StorageService,
    StoredObject,
    UploadKind,
    UploadStream,
)

logger = logging.getLogger(__name__)

BANNER_WIDTHS = (800, 1200, 2000)
BANNER_MIN_WIDTH = BANNER_WIDTHS[0]
BANNER_MAX_BYTES = 5 * 1024 * 1024
BANNER_MIME_TYPES = {"image/png", "image/jpeg", "image/webp"}
BANNER_CONTEXT = "event_banner"
BANNER_MIME_TYPE = "image/webp"
WEBP_QUALITY = 85
WEBP_METHOD = 6
RESAMPLING = Image.Resampling.LANCZOS


@dataclass(frozen=True)
class BannerVariant:
    width: int
    height: int
    content: bytes


def banner_widths(source_width: int) -> list[int]:
    largest = min(source_width, BANNER_WIDTHS[-1])
    return [width for width in BANNER_WIDTHS if width < largest] + [largest]


def render_variants(content: bytes, identifier: str) -> list[BannerVariant]:
    with Image.open(BytesIO(content)) as source:
        oriented = ImageOps.exif_transpose(source)
        mode = "RGBA" if oriented.has_transparency_data else "RGB"
        image = oriented.convert(mode)
    if image.width < BANNER_MIN_WIDTH:
        raise EventBannerTooSmall(f"{identifier}:width:{image.width}")
    variants: list[BannerVariant] = []
    for width in banner_widths(image.width):
        resized = ImageOps.contain(image, (width, image.height), RESAMPLING)
        buffer = BytesIO()
        resized.save(buffer, format="WEBP", quality=WEBP_QUALITY, method=WEBP_METHOD)
        variants.append(BannerVariant(resized.width, resized.height, buffer.getvalue()))
    return variants


class EventBannerService:
    def __init__(
        self,
        kp_repository: KpRepository,
        storage_service: StorageService,
        current_user: User,
    ) -> None:
        self.kp_repository = kp_repository
        self.storage_service = storage_service
        self.current_user = current_user

    async def _get_event(self, event_id: UUID) -> KpEvent:
        event = await self.kp_repository.get_by_id(event_id)
        if event is None:
            raise KpEventNotFound(f"{BANNER_CONTEXT}:{event_id}")
        return event

    async def _result(self, banner: KpEventBanner) -> EventBannerResult:
        sources = [
            EventBannerSource(
                width=variant.width,
                url=await self.storage_service.generate_download_url(
                    variant.stored_file.storage_key, f"banner-{variant.width}.webp"
                ),
            )
            for variant in banner.variants
        ]
        return EventBannerResult(
            width=banner.width, height=banner.height, sources=sources
        )

    async def banner_of(self, event: KpEvent) -> EventBannerResult | None:
        if event.banner_id is None:
            return None
        banner = await self.kp_repository.get_banner(event.banner_id)
        return None if banner is None else await self._result(banner)

    async def latest_event(self) -> KpLatestResult | None:
        event = await self.kp_repository.get_latest_kp()
        if event is None:
            return None
        latest = KpLatestResult.model_validate(event)
        return latest.model_copy(update={"banner": await self.banner_of(event)})

    async def get_banner(self, event_id: UUID) -> EventBannerResult | None:
        require_kp_president_user(self.current_user)
        return await self.banner_of(await self._get_event(event_id))

    async def upload_banner(
        self,
        event_id: UUID,
        upload: UploadStream,
        content_length: int | None,
        content_type: str | None,
    ) -> EventBannerResult:
        require_kp_president_user(self.current_user)
        event = await self._get_event(event_id)
        identifier = f"{BANNER_CONTEXT}:{event_id}"
        content = await self._read(upload, content_length, identifier)
        self.storage_service.validate_image_file(
            "banner",
            content,
            content_type,
            error_context=BANNER_CONTEXT,
            allowed_mime_types=BANNER_MIME_TYPES,
        )
        variants = await asyncio.to_thread(render_variants, content, identifier)
        stored = await self._store(event_id, variants)
        largest = variants[-1]
        previous_id = event.banner_id
        try:
            banner = await self.kp_repository.create_banner(
                largest.width,
                largest.height,
                [
                    (variant.width, self._stored_file(stored_object))
                    for variant, stored_object in zip(variants, stored, strict=True)
                ],
            )
            await self.kp_repository.set_event_banner(event, banner.id)
        except Exception:
            await self._delete_objects([stored_object.key for stored_object in stored])
            raise
        await self._release(previous_id)
        return await self._result(banner)

    async def reset_banner(self, event_id: UUID) -> None:
        require_kp_president_user(self.current_user)
        event = await self._get_event(event_id)
        previous_id = event.banner_id
        if previous_id is None:
            return
        await self.kp_repository.set_event_banner(event, None)
        await self._release(previous_id)

    async def _read(
        self, upload: UploadStream, content_length: int | None, identifier: str
    ) -> bytes:
        if content_length is not None and content_length > BANNER_MAX_BYTES:
            raise StorageFileTooLarge(f"{identifier}:size:{content_length}")
        content = await self.storage_service.read_upload(
            upload,
            content_length=content_length,
            kind=UploadKind.IMAGE,
            error_context=BANNER_CONTEXT,
        )
        if len(content) > BANNER_MAX_BYTES:
            raise StorageFileTooLarge(f"{identifier}:size:{len(content)}")
        return content

    async def _store(
        self, event_id: UUID, variants: list[BannerVariant]
    ) -> list[StoredObject]:
        prefix = f"kp/events/{event_id}/banner/{uuid4()}"
        stored: list[StoredObject] = []
        try:
            for variant in variants:
                stored.append(
                    await self.storage_service.upload_bytes(
                        key=f"{prefix}/{variant.width}.webp",
                        content=variant.content,
                        filename=f"banner-{variant.width}.webp",
                        content_type=BANNER_MIME_TYPE,
                    )
                )
        except Exception:
            await self._delete_objects([stored_object.key for stored_object in stored])
            raise
        return stored

    def _stored_file(self, stored_object: StoredObject) -> StoredFile:
        return StoredFile(
            storage_key=stored_object.key,
            original_filename=stored_object.key.rsplit("/", 1)[-1],
            mime_type=stored_object.mime_type,
            size_bytes=stored_object.size_bytes,
            sha256=stored_object.sha256,
            etag=stored_object.etag,
        )

    async def _delete_objects(self, keys: list[str]) -> bool:
        deleted = True
        for key in keys:
            try:
                await self.storage_service.delete_object(key)
            except StorageDeleteFailed:
                logger.warning("Event banner cleanup failed for %s", key)
                deleted = False
        return deleted

    async def _release(self, banner_id: UUID | None) -> None:
        if banner_id is None:
            return
        if await self.kp_repository.count_events_with_banner(banner_id):
            return
        banner = await self.kp_repository.get_banner(banner_id)
        if banner is None:
            return
        keys = [variant.stored_file.storage_key for variant in banner.variants]
        if await self._delete_objects(keys):
            await self.kp_repository.delete_banner(banner)
