import json
import tempfile
from pathlib import Path
from shutil import copyfile
from typing import Any

import typst

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
FONTS_DIR = TEMPLATES_DIR / "fonts"
PREVIEW_PPI = 110
PROBE_TEMPLATE = "pdf_probe.typ"
PROBE_SOURCE = "source.pdf"
PROBE_PPI = 1


class PdfUnreadable(ValueError):
    pass


def compile_pdf(template_path: str, data: dict[str, Any], root: str | None) -> bytes:
    return typst.compile(
        template_path,
        root=root,
        font_paths=[str(FONTS_DIR)],
        ignore_system_fonts=True,
        sys_inputs={"data": json.dumps(data)},
    )


def render_png(
    template_name: str,
    data: dict[str, Any],
    files: dict[str, bytes],
    metadata_label: str,
) -> tuple[bytes, Any]:
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
    return png, metadata


def _probe_page(root: Path, page: int) -> dict[str, float]:
    compiler = typst.Compiler(
        str(root / PROBE_TEMPLATE),
        root=str(root),
        font_paths=[str(FONTS_DIR)],
        ignore_system_fonts=True,
        sys_inputs={"source": PROBE_SOURCE, "page": str(page)},
    )
    compiler.compile(format="png", ppi=PROBE_PPI)
    return json.loads(compiler.query("<size>", field="value", one=True))


def inspect_pdf(content: bytes) -> tuple[float, float, bool]:
    with tempfile.TemporaryDirectory() as workspace:
        root = Path(workspace)
        copyfile(TEMPLATES_DIR / PROBE_TEMPLATE, root / PROBE_TEMPLATE)
        (root / PROBE_SOURCE).write_bytes(content)
        try:
            first = _probe_page(root, 1)
        except Exception as error:
            raise PdfUnreadable(str(error)) from None
        try:
            _probe_page(root, 2)
            has_more_pages = True
        except Exception:
            has_more_pages = False
    return float(first["width"]), float(first["height"]), has_more_pages
