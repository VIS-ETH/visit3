import json
from pathlib import Path

import pytest

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


async def test_render_with_workspace_copies_template_and_materializes_assets(
    monkeypatch, tmp_path
):
    service = PdfService()
    (tmp_path / "template.typ").write_text("#let data = json.decode(sys.inputs.at(\"data\"))")
    monkeypatch.setattr("app.services.pdf_service.TEMPLATES_DIR", tmp_path)
    captured: dict[str, object] = {}

    def fake_compile(path: str, *, root: str | None, sys_inputs: dict[str, str]):
        captured["path"] = path
        captured["root"] = root
        captured["sys_inputs"] = sys_inputs
        workspace = Path(root) if root else Path(path).parent
        assert (workspace / "template.typ").exists()
        assert (workspace / "asset.txt").read_text() == "extra"
        return b"%PDF"

    monkeypatch.setattr("app.services.pdf_service.typst.compile", fake_compile)

    async def materialize(workspace_path: Path) -> None:
        (workspace_path / "asset.txt").write_text("extra")

    content, filename = await service.render_with_workspace(
        "template.typ",
        {"key": "value"},
        "output.pdf",
        materialize=materialize,
    )

    assert content == b"%PDF"
    assert filename == "output.pdf"
    assert json.loads(captured["sys_inputs"]["data"]) == {"key": "value"}


async def test_render_with_workspace_raises_when_render_returns_none(
    monkeypatch, tmp_path
):
    service = PdfService()
    (tmp_path / "template.typ").write_text("template")
    monkeypatch.setattr("app.services.pdf_service.TEMPLATES_DIR", tmp_path)
    monkeypatch.setattr(
        "app.services.pdf_service.typst.compile", lambda *args, **kwargs: None
    )

    async def materialize(workspace_path: Path) -> None:
        pass

    with pytest.raises(RuntimeError, match="rendering_failed"):
        await service.render_with_workspace(
            "template.typ",
            {},
            "output.pdf",
            materialize=materialize,
        )
