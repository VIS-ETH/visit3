import asyncio
import json
import tempfile
from collections.abc import Awaitable, Callable
from pathlib import Path
from shutil import copyfile
from typing import Any

import typst

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


class PdfService:
    async def render(
        self,
        template_name: str,
        data: dict[str, Any],
        filename: str,
        root: str | None = None,
        template_dir: Path = TEMPLATES_DIR,
    ) -> tuple[None | bytes, str]:
        template_path = template_dir / template_name
        pdf_bytes = await asyncio.to_thread(
            typst.compile,
            str(template_path),
            root=root,
            sys_inputs={"data": json.dumps(data)},
        )
        return pdf_bytes, filename

    async def render_with_workspace(
        self,
        template_name: str,
        data: dict[str, Any],
        filename: str,
        materialize: Callable[[Path], Awaitable[None]],
    ) -> tuple[bytes, str]:
        """Render a Typst template inside a fresh temp workspace.

        The workspace starts with a copy of ``template_name`` from
        ``TEMPLATES_DIR``. ``materialize`` can then download additional
        assets into the workspace before compilation.
        """
        with tempfile.TemporaryDirectory() as workspace:
            workspace_path = Path(workspace)
            copyfile(
                TEMPLATES_DIR / template_name,
                workspace_path / template_name,
            )
            await materialize(workspace_path)
            content, rendered_filename = await self.render(
                template_name,
                data,
                filename,
                root=str(workspace_path),
                template_dir=workspace_path,
            )
        if content is None:
            raise RuntimeError(f"pdf_service:rendering_failed:{template_name}")
        return content, rendered_filename
