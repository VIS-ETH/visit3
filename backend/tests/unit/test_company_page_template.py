import json
from html import escape
from pathlib import Path
from shutil import copyfile
from typing import Any

import pytest
import typst

from app.core.rich_text import rich_text_blocks
from app.services.pdf_service import FONTS_DIR, TEMPLATES_DIR
from app.services.typst_worker import render_png
from tests.booklet_pdfs import make_pdf

TEMPLATE = "company_page.typ"
PROBE = """
#import "company_page.typ": company-description
#let entry = json(bytes(sys.inputs.at("data")))
#metadata(company-description(entry)) <description>
"""
HOSTILE_TEXTS = [
    '#panic("injected")',
    '#image("/etc/passwd")',
    "]] ) } #let x = 1",
    "*not bold* _not italic_",
    "$x^2$ and $ unbalanced",
    "back\\slash \\ #",
    "`code` ```raw```",
    "see <label> @reference // not a comment /* nor this */",
    '#{ panic("x") }',
    "= Heading\n- list",
]


def describe(tmp_path: Path, description: str) -> Any:
    copyfile(TEMPLATES_DIR / TEMPLATE, tmp_path / TEMPLATE)
    (tmp_path / "probe.typ").write_text(PROBE)
    compiler = typst.Compiler(
        str(tmp_path / "probe.typ"),
        root=str(tmp_path),
        font_paths=[str(FONTS_DIR)],
        ignore_system_fonts=True,
        sys_inputs={
            "data": json.dumps({"description_blocks": rich_text_blocks(description)})
        },
    )
    return json.loads(compiler.query("<description>", field="value", one=True))


def texts(node: Any) -> list[str]:
    if isinstance(node, dict):
        found = [node["text"]] if isinstance(node.get("text"), str) else []
        return found + [text for value in node.values() for text in texts(value)]
    if isinstance(node, list):
        return [text for value in node for text in texts(value)]
    return []


def wrappers(node: Any, text: str, trail: tuple[str, ...] = ()) -> set[str]:
    if isinstance(node, dict):
        func = node.get("func")
        path = (*trail, func) if isinstance(func, str) else trail
        if node.get("text") == text:
            return set(path)
        return {name for value in node.values() for name in wrappers(value, text, path)}
    if isinstance(node, list):
        return {name for value in node for name in wrappers(value, text, trail)}
    return set()


@pytest.mark.parametrize("hostile", HOSTILE_TEXTS)
def test_company_text_is_never_evaluated_as_typst(tmp_path: Path, hostile: str):
    paragraphs = [line for line in hostile.split("\n") if line.strip()]

    rendered = describe(tmp_path, hostile)

    assert texts(rendered) == paragraphs


def test_the_formatting_marks_are_rendered(tmp_path: Path):
    rendered = describe(
        tmp_path,
        "<p><strong>bold</strong><em>italic</em><u>under</u><s>gone</s>"
        "<strong><em>both</em></strong></p>",
    )

    assert "strong" in wrappers(rendered, "bold")
    assert "emph" in wrappers(rendered, "italic")
    assert "underline" in wrappers(rendered, "under")
    assert "strike" in wrappers(rendered, "gone")
    assert {"strong", "emph"} <= wrappers(rendered, "both")
    assert "strong" not in wrappers(rendered, "gone")


def test_paragraphs_and_line_breaks_are_kept(tmp_path: Path):
    rendered = describe(tmp_path, "<p>one<br>two</p><p>three</p>")

    serialized = json.dumps(rendered)
    assert serialized.count('"func": "par"') == 2
    assert serialized.count('"func": "linebreak"') == 1
    assert texts(rendered) == ["one", "two", "three"]


MARKERS = {"•", "–"}


def nodes(node: Any, func: str) -> list[dict[str, Any]]:
    if isinstance(node, dict):
        found = [node] if node.get("func") == func else []
        return found + [
            inner for value in node.values() for inner in nodes(value, func)
        ]
    if isinstance(node, list):
        return [inner for value in node for inner in nodes(value, func)]
    return []


@pytest.mark.parametrize("hostile", HOSTILE_TEXTS)
def test_list_items_are_never_evaluated_as_typst(tmp_path: Path, hostile: str):
    lines = [line for line in hostile.split("\n") if line.strip()]
    items = "".join(f"<li><p>{escape(line)}</p></li>" for line in lines)

    rendered = describe(
        tmp_path, f"<ul><li><p>x</p><ol>{items}</ol></li></ul><ol>{items}</ol>"
    )

    assert [text for text in texts(rendered) if text not in MARKERS] == [
        "x",
        *lines,
        *lines,
    ]


def test_lists_render_with_their_markers_and_one_nesting_level(tmp_path: Path):
    rendered = describe(
        tmp_path,
        "<ul><li><p>a</p><ul><li><p>b</p></li></ul><ol><li><p>c</p></li></ol></li>"
        "</ul><ol><li><p>d</p><ol><li><p>e</p></li></ol></li></ol>",
    )

    bullets = nodes(rendered, "list")
    numbers = nodes(rendered, "enum")
    assert [texts(node["marker"]) for node in bullets] == [["•"], ["–"]]
    assert [node["numbering"] for node in numbers] == ["a.", "1.", "a."]
    assert [node["breakable"] for node in nodes(rendered, "block")] == [False, False]
    assert [text for text in texts(rendered) if text not in MARKERS] == list("abcde")


def test_list_items_keep_their_formatting_and_line_breaks(tmp_path: Path):
    rendered = describe(
        tmp_path, "<ol><li><p><strong>bold</strong><br><em>next</em></p></li></ol>"
    )

    assert "strong" in wrappers(rendered, "bold")
    assert "emph" in wrappers(rendered, "next")
    assert len(nodes(rendered, "linebreak")) == 1


def test_a_blank_line_takes_the_height_of_one_empty_paragraph(tmp_path: Path):
    rendered = describe(tmp_path, "<p>one</p><p></p><p>two</p>")

    assert len(nodes(rendered, "par")) == 3
    assert len(nodes(rendered, "hide")) == 1
    assert [text for text in texts(rendered) if text != "x"] == ["one", "two"]


SIDEBAR_PROBE = """
#import "company_page.typ": company-sidebar
#let entry = json(bytes(sys.inputs.at("data")))
#metadata(company-sidebar(entry)) <sidebar>
"""


def test_the_sidebar_keeps_the_contact_data_internal(tmp_path: Path):
    copyfile(TEMPLATES_DIR / TEMPLATE, tmp_path / TEMPLATE)
    (tmp_path / "probe.typ").write_text(SIDEBAR_PROBE)
    compiler = typst.Compiler(
        str(tmp_path / "probe.typ"),
        root=str(tmp_path),
        font_paths=[str(FONTS_DIR)],
        ignore_system_fonts=True,
        sys_inputs={
            "data": json.dumps(
                {
                    "general_email": "internal@acme.example",
                    "general_phone": "+41 44 000 00 00",
                    "website": "https://acme.example",
                }
            )
        },
    )

    rendered = texts(json.loads(compiler.query("<sidebar>", field="value", one=True)))

    assert "https://acme.example" in rendered
    assert "CONTACT" not in rendered
    assert "internal@acme.example" not in rendered
    assert "+41 44 000 00 00" not in rendered


EMAIL_PROBE = """
#import "company_page.typ": email-lines, sidebar-inner-width, sidebar-value-size
#set text(font: "DejaVu Sans")
#let address = sys.inputs.at("address")
#context {
  let lines = email-lines(address, sidebar-inner-width)
  let widths = lines.map(line => measure(text(size: sidebar-value-size, line)).width / 1pt)
  [#metadata((lines: lines, widths: widths, limit: sidebar-inner-width / 1pt)) <lines>]
}
"""
NORMAL_ADDRESS = "jobs@acme.example"
LONG_ADDRESSES = [
    "karriere.studierende-kontakt@beispiel-robotics-engineering.example.com",
    "studierendenkontaktkarriere@beispielroboticsengineeringgruppe.example.com",
    "a" * 64 + "@" + "b" * 60 + ".example.com",
    "a#b$c*d_e`f<g>h@acme.example",
]
SEPARATOR_ADDRESS = LONG_ADDRESSES[0]


def compile_probe(tmp_path: Path, probe: str, inputs: dict[str, str]) -> typst.Compiler:
    copyfile(TEMPLATES_DIR / TEMPLATE, tmp_path / TEMPLATE)
    (tmp_path / "probe.typ").write_text(probe)
    return typst.Compiler(
        str(tmp_path / "probe.typ"),
        root=str(tmp_path),
        font_paths=[str(FONTS_DIR)],
        ignore_system_fonts=True,
        sys_inputs=inputs,
    )


def email_lines(tmp_path: Path, address: str) -> dict[str, Any]:
    compiler = compile_probe(tmp_path, EMAIL_PROBE, {"address": address})
    return json.loads(compiler.query("<lines>", field="value", one=True))


def sidebar_texts(tmp_path: Path, entry: dict[str, object]) -> list[str]:
    compiler = compile_probe(tmp_path, SIDEBAR_PROBE, {"data": json.dumps(entry)})
    return texts(json.loads(compiler.query("<sidebar>", field="value", one=True)))


def test_a_normal_student_email_stays_on_one_line(tmp_path: Path):
    assert email_lines(tmp_path, NORMAL_ADDRESS)["lines"] == [NORMAL_ADDRESS]


@pytest.mark.parametrize("address", LONG_ADDRESSES)
def test_a_long_student_email_wraps_inside_the_sidebar(tmp_path: Path, address: str):
    probed = email_lines(tmp_path, address)

    assert "".join(probed["lines"]) == address
    assert all(width <= probed["limit"] for width in probed["widths"])


def test_a_long_student_email_breaks_at_its_separators(tmp_path: Path):
    lines = email_lines(tmp_path, SEPARATOR_ADDRESS)["lines"]

    assert len(lines) > 1
    assert all(line.startswith((".", "@", "-", "_")) for line in lines[1:])


def test_the_sidebar_shows_the_student_contact_above_the_website(tmp_path: Path):
    rendered = sidebar_texts(
        tmp_path,
        {"student_contact_email": NORMAL_ADDRESS, "website": "https://acme.example"},
    )

    assert rendered.index("CONTACT") < rendered.index("WEBSITE")


def test_the_sidebar_has_no_contact_block_without_a_student_email(tmp_path: Path):
    rendered = sidebar_texts(tmp_path, {"website": "https://acme.example"})

    assert "CONTACT" not in rendered


@pytest.mark.parametrize("with_background", [False, True])
@pytest.mark.parametrize("address", [NORMAL_ADDRESS, *LONG_ADDRESSES])
def test_a_page_with_a_student_email_renders_without_overflow(
    address: str, with_background: bool
):
    files = {"background.pdf": make_pdf(fill="#fde68a")} if with_background else {}

    png, overflow = render_png(
        TEMPLATE,
        {
            "company": "Acme AG",
            "student_contact_email": address,
            "website": "https://acme.example",
            "background_path": "background.pdf" if with_background else None,
        },
        files,
        "overflow",
    )

    assert png.startswith(b"\x89PNG")
    assert overflow is False
