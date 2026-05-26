import json

from app.services.pdf_service import PdfService


async def test_render_passes_user_data_as_json_sys_input(monkeypatch, tmp_path):
    service = PdfService()
    template = tmp_path / "template.typ"
    template.write_text('#let data = json.decode(sys.inputs.at("data"))')
    captured: dict[str, object] = {}

    def fake_compile(path: str, *, root: str | None, sys_inputs: dict[str, str]):
        captured["path"] = path
        captured["root"] = root
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
    assert json.loads(captured["sys_inputs"]["data"]) == data
