import json
import tempfile
from pathlib import Path
from shutil import copyfile

import typst

from app.services.pdf_service import FONTS_DIR, TEMPLATES_DIR
from tests.booklet_pdfs import make_pdf

ZONE_COLOR = "#e53935"


def render_svg(background: bytes | None) -> str:
    entry = {
        "company": "Acme AG",
        "brand_name": "Acme",
        "description_blocks": [[{"text": "We build anvils."}]],
        "zone_color": ZONE_COLOR,
        "background_path": "background.pdf" if background is not None else None,
    }
    with tempfile.TemporaryDirectory() as workspace:
        root = Path(workspace)
        copyfile(TEMPLATES_DIR / "company_page.typ", root / "company_page.typ")
        if background is not None:
            (root / "background.pdf").write_bytes(background)
        svg = typst.compile(
            str(root / "company_page.typ"),
            root=str(root),
            format="svg",
            font_paths=[str(FONTS_DIR)],
            ignore_system_fonts=True,
            sys_inputs={"data": json.dumps(entry)},
        )
    assert isinstance(svg, bytes)
    return svg.decode()


def test_the_default_page_draws_the_zone_stripe():
    assert ZONE_COLOR in render_svg(None)


def test_a_background_replaces_the_zone_stripe():
    svg = render_svg(make_pdf(fill="#0055aa"))

    assert ZONE_COLOR not in svg
    assert "<image" in svg or "#0055aa" in svg.lower()


def test_the_default_page_has_no_background_image():
    svg = render_svg(None)

    assert "<image" not in svg
