from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from app.services.csv_service import CsvService
from app.services.export_service import NAMETAG_TEMPLATE_NAME, ExportService


class FakePdfService:
    def __init__(self) -> None:
        self.rendered_data: dict[str, object] | None = None
        self.rendered_filename: str | None = None

    async def render(
        self,
        template_name: str,
        data: dict[str, object],
        filename: str,
        root: str | None = None,
        template_dir: Path | None = None,
    ):
        assert root is not None
        root_path = Path(root)
        assert template_dir == root_path
        assert template_name == NAMETAG_TEMPLATE_NAME
        assert data["background_path"] == "background.png"
        assert (root_path / "background.png").read_bytes() == b"\x89PNG\r\n"
        self.rendered_data = data
        self.rendered_filename = filename
        return b"%PDF", filename


async def test_nametag_pdf_render_uses_restricted_workspace_and_json_data():
    pdf_service = FakePdfService()
    service = ExportService(
        kp_repository=Mock(),
        storage_service=Mock(),
        pdf_service=pdf_service,
        csv_service=CsvService(),
        current_user=Mock(),
    )
    name_tag = SimpleNamespace(
        first_name='#panic("boom")',
        last_name="Person",
        position="#image('/etc/passwd')",
        booking=SimpleNamespace(company=SimpleNamespace(name="=Company")),
    )

    export = await service._render_nametags_pdf(
        b"\x89PNG\r\n",
        "image/png",
        [name_tag],
        '../"nametag\r.pdf',
        1,
    )

    assert export.content == b"%PDF"
    assert export.filename == "nametag.pdf"
    assert pdf_service.rendered_data is not None
    assert pdf_service.rendered_data["tags"] == [
        {
            "full_name": '#panic("boom") Person',
            "position": "#image('/etc/passwd')",
            "company": "=Company",
        }
    ]
