import asyncio
import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from shutil import copyfile
from typing import Any

import typst

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
FONTS_DIR = TEMPLATES_DIR / "fonts"
PREVIEW_PPI = 110


@dataclass(frozen=True)
class RenderedImage:
    png: bytes
    metadata: Any


def _render_png(
    template_name: str,
    data: dict[str, Any],
    files: dict[str, bytes],
    metadata_label: str,
) -> RenderedImage:
    with tempfile.TemporaryDirectory() as workspace:
        root = Path(workspace)
        copyfile(TEMPLATES_DIR / template_name, root / template_name)
        for name, content in files.items():
            (root / name).write_bytes(content)
        compiler = typst.Compiler(
            str(root / template_name),
            root=str(root),
            font_paths=[str(FONTS_DIR)],
            ignore_system_fonts=True,
            sys_inputs={"data": json.dumps(data)},
        )
        png = compiler.compile(format="png", ppi=PREVIEW_PPI)
        metadata = json.loads(
            compiler.query(f"<{metadata_label}>", field="value", one=True)
        )
    if not isinstance(png, bytes):
        raise ValueError(f"render_png:{template_name}:expected_one_page")
    return RenderedImage(png=png, metadata=metadata)


class PdfService:
    async def render(
        self,
        template_name: str,
        data: dict[str, Any],
        filename: str,
        root: str | None = None,
        template_dir: Path = TEMPLATES_DIR,
    ) -> tuple[None | bytes, str]:
        template_path = template_dir / template_name
        pdf_bytes = await asyncio.to_thread(
            typst.compile,
            str(template_path),
            root=root,
            font_paths=[str(FONTS_DIR)],
            ignore_system_fonts=True,
            sys_inputs={"data": json.dumps(data)},
        )
        return pdf_bytes, filename

    async def render_png(
        self,
        *,
        template_name: str,
        data: dict[str, Any],
        files: dict[str, bytes],
        metadata_label: str,
    ) -> RenderedImage:
        return await asyncio.to_thread(
            _render_png, template_name, data, files, metadata_label
        )
