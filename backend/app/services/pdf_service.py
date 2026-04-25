import asyncio
import json
from pathlib import Path

import typst

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


class PdfService:
    async def render(
        self, template_name: str, data: dict, filename: str
    ) -> tuple[bytes, str]:
        template_path = TEMPLATES_DIR / template_name
        pdf_bytes = await asyncio.to_thread(
            typst.compile,
            str(template_path),
            sys_inputs={"data": json.dumps(data)},
        )
        return pdf_bytes, filename
