import json
from base64 import b64decode
from shutil import copyfile

import typst

from app.models.company import PROFILE_DESCRIPTION_MAX_LENGTH
from app.services.export_service import NAMETAG_TEMPLATE_NAME
from app.services.pdf_service import FONTS_DIR, TEMPLATES_DIR, PdfService

ONE_PIXEL_PNG = b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


async def test_render_passes_user_data_as_json_sys_input(monkeypatch, tmp_path):
    service = PdfService()
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

    monkeypatch.setattr("app.services.pdf_service.typst.compile", fake_compile)

    data = {"name": '#panic("boom")', "company": "#image('/etc/passwd')"}
    content, filename = await service.render(
        template.name,
        data,
        "nametag.pdf",
        root=str(tmp_path),
        template_dir=tmp_path,
    )

    assert content == b"%PDF"
    assert filename == "nametag.pdf"
    assert captured["path"] == str(template)
    assert captured["root"] == str(tmp_path)
    assert captured["font_paths"] == [str(FONTS_DIR)]
    assert captured["ignore_system_fonts"] is True
    assert json.loads(captured["sys_inputs"]["data"]) == data


def test_bundled_fonts_provide_dejavu_sans():
    fonts = typst.Fonts(
        include_system_fonts=False,
        include_embedded_fonts=False,
        font_paths=[str(FONTS_DIR)],
    )

    assert {(font.family, font.weight) for font in fonts.fonts()} == {
        ("DejaVu Sans", 400),
        ("DejaVu Sans", 700),
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
        "description": "Wir bauen Roboter.",
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
        data=company_page_entry(description="Zeile\n" * 400),
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
            description=(sentence * 30)[:PROFILE_DESCRIPTION_MAX_LENGTH],
            logo_path="logo.png",
        ),
        files={"logo.png": ONE_PIXEL_PNG},
        metadata_label="overflow",
    )

    assert rendered.metadata is False
