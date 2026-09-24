import json
from base64 import b64decode
from shutil import copyfile

import typst

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
