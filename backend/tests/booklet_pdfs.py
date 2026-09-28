import tempfile
from pathlib import Path

import typst

A5_WIDTH_MM = 148
A5_HEIGHT_MM = 210


def make_pdf(
    width_mm: float = A5_WIDTH_MM,
    height_mm: float = A5_HEIGHT_MM,
    pages: int = 1,
    fill: str = "#ffffff",
) -> bytes:
    page = f'#rect(width: 100%, height: 100%, fill: rgb("{fill}"))'
    body = "\n#pagebreak()\n".join(page for _ in range(pages))
    with tempfile.TemporaryDirectory() as workspace:
        source = Path(workspace) / "background.typ"
        source.write_text(
            f"#set page(width: {width_mm}mm, height: {height_mm}mm, margin: 0mm)\n"
            f"{body}\n"
        )
        content = typst.compile(str(source))
    assert isinstance(content, bytes)
    return content
