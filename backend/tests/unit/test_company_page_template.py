import json
from pathlib import Path
from shutil import copyfile
from typing import Any

import pytest
import typst

from app.core.rich_text import rich_text_blocks
from app.services.pdf_service import FONTS_DIR, TEMPLATES_DIR

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
