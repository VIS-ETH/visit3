from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.services import typst_worker
from app.services.typst_runner import typst_runner
from app.services.typst_worker import FONTS_DIR, TEMPLATES_DIR, PdfUnreadable

__all__ = [
    "FONTS_DIR",
    "TEMPLATES_DIR",
    "PdfPage",
    "PdfService",
    "PdfUnreadable",
    "RenderedImage",
]


@dataclass(frozen=True)
class PdfPage:
    width_mm: float
    height_mm: float
    has_more_pages: bool


@dataclass(frozen=True)
class RenderedImage:
    png: bytes
    metadata: Any


class PdfService:
    async def inspect_pdf(
        self, content: bytes, timeout: float | None = None
    ) -> PdfPage:
        width_mm, height_mm, has_more_pages = await typst_runner().run(
            typst_worker.inspect_pdf,
            (content,),
            timeout or get_settings().TYPST_VALIDATION_TIMEOUT_SECONDS,
        )
        return PdfPage(
            width_mm=width_mm, height_mm=height_mm, has_more_pages=has_more_pages
        )

    async def render(
        self,
        template_name: str,
        data: dict[str, Any],
        filename: str,
        root: str | None = None,
        template_dir: Path = TEMPLATES_DIR,
    ) -> tuple[None | bytes, str]:
        pdf_bytes = await typst_runner().run(
            typst_worker.compile_pdf,
            (str(template_dir / template_name), data, root),
            get_settings().TYPST_EXPORT_TIMEOUT_SECONDS,
        )
        return pdf_bytes, filename

    async def render_png(
        self,
        *,
        template_name: str,
        data: dict[str, Any],
        files: dict[str, bytes],
        metadata_label: str,
        timeout: float | None = None,
    ) -> RenderedImage:
        png, metadata = await typst_runner().run(
            typst_worker.render_png,
            (template_name, data, files, metadata_label),
            timeout or get_settings().TYPST_PREVIEW_TIMEOUT_SECONDS,
        )
        return RenderedImage(png=png, metadata=metadata)
