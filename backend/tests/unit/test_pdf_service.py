import json
import time
from base64 import b64decode
from shutil import copyfile

import pytest
import typst

from app.core.rich_text import (
    rich_text_blocks,
    rich_text_length,
    sanitize_rich_text,
)
from app.models.company import PROFILE_DESCRIPTION_MAX_LENGTH
from app.services.export_service import NAMETAG_TEMPLATE_NAME
from app.services.pdf_service import FONTS_DIR, TEMPLATES_DIR, PdfService
from app.services.typst_runner import TypstRenderAborted
from app.services.typst_worker import compile_pdf

ONE_PIXEL_PNG = b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def test_render_passes_user_data_as_json_sys_input(monkeypatch, tmp_path):
    template = tmp_path / "template.typ"
    template.write_text('#let data = json(bytes(sys.inputs.at("data")))')
    captured: dict[str, object] = {}

    def fake_compile(
        path: str,
        *,
        root: str | None,
        font_paths: list[str],
        ignore_system_fonts: bool,
        sys_inputs: dict[str, str],
    ):
        captured["path"] = path
        captured["root"] = root
        captured["font_paths"] = font_paths
        captured["ignore_system_fonts"] = ignore_system_fonts
        captured["sys_inputs"] = sys_inputs
        return b"%PDF"

    monkeypatch.setattr("app.services.typst_worker.typst.compile", fake_compile)

    data = {"name": '#panic("boom")', "company": "#image('/etc/passwd')"}
    content = compile_pdf(str(template), data, str(tmp_path))

    assert content == b"%PDF"
    assert captured["path"] == str(template)
    assert captured["root"] == str(tmp_path)
    assert captured["font_paths"] == [str(FONTS_DIR)]
    assert captured["ignore_system_fonts"] is True
    assert json.loads(captured["sys_inputs"]["data"]) == data


def test_bundled_fonts_provide_every_dejavu_sans_style():
    fonts = typst.Fonts(
        include_system_fonts=False,
        include_embedded_fonts=False,
        font_paths=[str(FONTS_DIR)],
    )

    assert {(font.family, font.weight, font.style) for font in fonts.fonts()} == {
        ("DejaVu Sans", 400, "normal"),
        ("DejaVu Sans", 700, "normal"),
        ("DejaVu Sans", 400, "italic"),
        ("DejaVu Sans", 700, "italic"),
    }


async def test_render_compiles_nametag_template(tmp_path):
    copyfile(TEMPLATES_DIR / NAMETAG_TEMPLATE_NAME, tmp_path / NAMETAG_TEMPLATE_NAME)
    (tmp_path / "background.png").write_bytes(ONE_PIXEL_PNG)

    content, filename = await PdfService().render(
        NAMETAG_TEMPLATE_NAME,
        {
            "background_path": "background.png",
            "columns": 2,
            "tags": [
                {
                    "full_name": "Ada Lovelace",
                    "position": "Engineer",
                    "company": "ACME",
                }
            ],
        },
        "nametag.pdf",
        root=str(tmp_path),
        template_dir=tmp_path,
    )

    assert content is not None
    assert content.startswith(b"%PDF")
    assert filename == "nametag.pdf"


def company_page_entry(**overrides: object) -> dict[str, object]:
    return {
        "company": "Acme AG",
        "brand_name": "Acme Labs",
        "description_blocks": rich_text_blocks("<p>Wir bauen Roboter.</p>"),
        "general_email": "info@acme.example",
        "languages": ["German"],
        "industries": ["Robotics"],
        "offers": {"internships": True},
        **overrides,
    }


async def test_render_png_draws_one_company_page_with_its_logo():
    rendered = await PdfService().render_png(
        template_name="company_page.typ",
        data=company_page_entry(logo_path="logo.png", zone_color="#112233"),
        files={"logo.png": ONE_PIXEL_PNG},
        metadata_label="overflow",
    )

    assert rendered.png.startswith(b"\x89PNG\r\n\x1a\n")
    assert rendered.metadata is False


async def test_render_png_reports_a_company_page_that_overflows():
    rendered = await PdfService().render_png(
        template_name="company_page.typ",
        data=company_page_entry(description_blocks=rich_text_blocks("Zeile\n" * 400)),
        files={},
        metadata_label="overflow",
    )

    assert rendered.metadata is True


async def test_a_full_description_of_the_limit_fits_the_company_page():
    sentence = (
        "Die Acme Robotics AG entwickelt autonome Inspektionsroboter für "
        "Industrieanlagen und Infrastrukturbetreiber in der ganzen Schweiz. "
    )
    rendered = await PdfService().render_png(
        template_name="company_page.typ",
        data=company_page_entry(
            description_blocks=rich_text_blocks(
                "<p><strong>Acme Robotics</strong> <em>entwickelt</em> "
                "<u>autonome</u> <s>Roboter</s> "
                + (sentence * 30)[: PROFILE_DESCRIPTION_MAX_LENGTH - 42]
                + "</p>"
            ),
            logo_path="logo.png",
        ),
        files={"logo.png": ONE_PIXEL_PNG},
        metadata_label="overflow",
    )

    assert rendered.metadata is False


async def test_a_fully_bold_description_of_the_limit_reports_the_overflow():
    sentence = (
        "Die Acme Robotics AG entwickelt autonome Inspektionsroboter für "
        "Industrieanlagen und Infrastrukturbetreiber in der ganzen Schweiz. "
    )
    rendered = await PdfService().render_png(
        template_name="company_page.typ",
        data=company_page_entry(
            description_blocks=rich_text_blocks(
                "<p><strong>"
                + (sentence * 30)[:PROFILE_DESCRIPTION_MAX_LENGTH]
                + "</strong></p>"
            ),
        ),
        files={},
        metadata_label="overflow",
    )

    assert rendered.metadata is True


def items(*texts: str) -> str:
    return "".join(f"<li><p>{text}</p></li>" for text in texts)


STRUCTURED_DESCRIPTION = (
    "<p><strong>Acme Robotics AG</strong> entwickelt autonome Inspektionsroboter "
    "für Industrieanlagen, Tunnel und Kraftwerke in der ganzen Schweiz. Unsere "
    "Teams in Zürich und Lausanne verbinden Mechatronik, Machine Learning und "
    "Software Engineering zu Produkten, die täglich im Einsatz sind.</p>"
    "<p><strong>Was wir bieten:</strong></p><ul>"
    + items(
        "Praktika von drei bis sechs Monaten in Hardware, Software oder Data "
        "Science, mit echter Verantwortung ab dem ersten Tag",
        "Bachelor- und Masterarbeiten in Kooperation mit der ETH Zürich und der "
        "EPFL, betreut von erfahrenen Ingenieurinnen und Ingenieuren",
        "Teilzeitstellen für Studierende mit flexiblen Arbeitszeiten",
        "Einstiegsstellen in einem interdisziplinären Team mit flachen Hierarchien",
    )
    + "</ul><p><strong>Unsere Teams:</strong></p><ul><li><p>Robotik</p><ul>"
    + items(
        "Antriebe, Sensorik und Leistungselektronik für raue Umgebungen",
        "Konstruktion und Prototyping in unserer eigenen Werkstatt",
    )
    + "</ul></li><li><p>Software</p><ol>"
    + items(
        "Perception, Lokalisierung und Navigation in Echtzeit",
        "Cloud-Plattform für Inspektionsdaten und Berichte",
    )
    + "</ol></li></ul><p><strong>So bewirbst du dich:</strong></p><ol>"
    + items(
        "Online-Bewerbung mit Lebenslauf und Notenauszug über die Karriereseite",
        "Kurzes Kennenlernen per Video mit dem Team, in dem du arbeiten wirst",
        "Technisches Gespräch vor Ort mit einer kleinen praktischen Aufgabe",
    )
    + "</ol><p></p><p>Besuche uns am Stand und lerne unsere Roboter live kennen."
    "<br>Kontakt: Personalabteilung, Technoparkstrasse 1, 8005 Zürich</p>"
)


async def render_description(html: str) -> object:
    rendered = await PdfService().render_png(
        template_name="company_page.typ",
        data=company_page_entry(
            description_blocks=rich_text_blocks(sanitize_rich_text(html)),
            logo_path="logo.png",
        ),
        files={"logo.png": ONE_PIXEL_PNG},
        metadata_label="overflow",
    )
    return rendered.metadata


async def test_a_structured_description_with_lists_fits_the_company_page():
    assert rich_text_length(sanitize_rich_text(STRUCTURED_DESCRIPTION)) > 1200

    assert await render_description(STRUCTURED_DESCRIPTION) is False


async def test_a_list_heavy_description_of_the_limit_reports_the_overflow():
    entry = "Wir bieten Praktika"
    count = (PROFILE_DESCRIPTION_MAX_LENGTH + 1) // (len(entry) + 1)
    html = "<ul>" + items(*[entry] * count) + "</ul>"

    assert rich_text_length(html) == PROFILE_DESCRIPTION_MAX_LENGTH - 1
    assert await render_description(html) is True


@pytest.mark.parametrize(
    "html",
    [
        "<ul>" + items(*"x" * 1250) + "</ul>",
        "<ol>" + "<li><p>x</p><ul><li><p>y</p></li></ul></li>" * 625 + "</ol>",
        "<p>x</p><p></p>" * 834,
        "<p>" + "x<br><br>" * 834 + "</p>",
    ],
)
async def test_the_densest_descriptions_render_well_within_the_limit(html: str):
    started = time.monotonic()

    rendered = await PdfService().render_png(
        template_name="company_page.typ",
        data=company_page_entry(
            description_blocks=rich_text_blocks(sanitize_rich_text(html))
        ),
        files={},
        metadata_label="overflow",
        timeout=10,
    )

    assert rendered.metadata is True
    assert time.monotonic() - started < 3


def endless_description() -> list[list[dict[str, object]]]:
    return [[{"text": "Wort " * 20, "bold": True}] for _ in range(20000)]


async def test_a_company_page_that_renders_too_long_is_aborted():
    started = time.monotonic()

    with pytest.raises(TypstRenderAborted):
        await PdfService().render_png(
            template_name="company_page.typ",
            data=company_page_entry(description_blocks=endless_description()),
            files={},
            metadata_label="overflow",
            timeout=1,
        )

    assert time.monotonic() - started < 4


async def test_a_normal_company_page_renders_well_within_the_limit():
    started = time.monotonic()

    rendered = await PdfService().render_png(
        template_name="company_page.typ",
        data=company_page_entry(),
        files={},
        metadata_label="overflow",
        timeout=10,
    )

    assert rendered.png.startswith(b"\x89PNG\r\n\x1a\n")
    assert time.monotonic() - started < 3
