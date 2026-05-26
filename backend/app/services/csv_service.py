import csv
import io
import zipfile
from datetime import date, datetime
from uuid import UUID

from app.core.downloads import sanitize_download_filename

FORMULA_PREFIXES = ("=", "+", "-", "@")
LEADING_CONTROL_PREFIXES = ("\t", "\r", "\n")


def _csv_value(value: object) -> object:
    if value is None:
        return ""
    if isinstance(value, str):
        return _escape_formula(value)
    if isinstance(value, (bool, int, float, UUID, date, datetime)):
        return value
    return _escape_formula(str(value))


def _escape_formula(value: str) -> str:
    stripped = value.lstrip()
    if value.startswith(LEADING_CONTROL_PREFIXES):
        return f"'{value}"
    if stripped.startswith(FORMULA_PREFIXES):
        return f"'{value}"
    return value


class CsvService:
    def render_csv(
        self,
        rows: list[dict[str, object]],
        filename: str,
        fieldnames: list[str] | None = None,
    ) -> tuple[bytes, str]:
        output = io.StringIO(newline="")
        fieldnames = fieldnames or (list(rows[0].keys()) if rows else [])
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(
            {
                field_name: _csv_value(row.get(field_name, ""))
                for field_name in fieldnames
            }
            for row in rows
        )
        return output.getvalue().encode("utf-8-sig"), sanitize_download_filename(
            filename
        )

    def render_zip(
        self, files: list[tuple[str, bytes]], filename: str
    ) -> tuple[bytes, str]:
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for file_name, content in files:
                archive.writestr(sanitize_download_filename(file_name), content)
        return output.getvalue(), sanitize_download_filename(filename)
