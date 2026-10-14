import json
import re
from pathlib import Path
from shutil import copyfile

import pytest
import typst

from app.services.pdf_service import FONTS_DIR, TEMPLATES_DIR
from tests.unit.test_booklet_background_template import render_svg

TEMPLATE = "company_page.typ"
LIGHT_TURQUOISE = "#7fdbd0"
DARK_NAVY = "#1e3a5f"
MINIMUM_CONTRAST = 4.5
PROBE = """
#import "company_page.typ": sidebar-ink
#metadata(sidebar-ink(rgb(sys.inputs.at("color"))).to-hex()) <ink>
"""
ZONE_COLORS = [
    LIGHT_TURQUOISE,
    DARK_NAVY,
    "#4b5563",
    "#e53935",
    "#ffe210",
    "#767676",
    "#777777",
    "#ffffff",
    "#000000",
]


def linear(channel: int) -> float:
    ratio = channel / 255
    return ratio / 12.92 if ratio <= 0.04045 else ((ratio + 0.055) / 1.055) ** 2.4


def luminance(color: str) -> float:
    red, green, blue = (int(color[index : index + 2], 16) for index in (1, 3, 5))
    return 0.2126 * linear(red) + 0.7152 * linear(green) + 0.0722 * linear(blue)


def contrast(first: str, second: str) -> float:
    lighter, darker = sorted((luminance(first), luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def sidebar_ink(tmp_path: Path, color: str) -> str:
    copyfile(TEMPLATES_DIR / TEMPLATE, tmp_path / TEMPLATE)
    (tmp_path / "probe.typ").write_text(PROBE)
    compiler = typst.Compiler(
        str(tmp_path / "probe.typ"),
        root=str(tmp_path),
        font_paths=[str(FONTS_DIR)],
        ignore_system_fonts=True,
        sys_inputs={"color": color},
    )
    return json.loads(compiler.query("<ink>", field="value", one=True))


def foreground_colors(svg: str) -> set[str]:
    glyphs = re.findall(r'<use[^>]*fill="(#[0-9a-f]{6,8})"', svg)
    strokes = re.findall(r'stroke="(#[0-9a-f]{6,8})"', svg)
    return {*glyphs, *strokes}


@pytest.mark.parametrize("color", ZONE_COLORS)
def test_the_sidebar_text_is_readable_on_every_zone_color(tmp_path: Path, color: str):
    assert contrast(sidebar_ink(tmp_path, color), color) >= MINIMUM_CONTRAST


def test_a_light_turquoise_sidebar_is_written_in_black():
    colors = foreground_colors(render_svg(None, LIGHT_TURQUOISE))

    assert colors == {"#000000", "#5f6368"}


def test_a_dark_sidebar_keeps_its_white_text():
    colors = foreground_colors(render_svg(None, DARK_NAVY))

    assert colors == {"#000000", "#5f6368", "#ffffff"}
