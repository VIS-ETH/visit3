import csv
import io
import zipfile


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
        writer.writerows(rows)
        return output.getvalue().encode("utf-8-sig"), filename

    def render_zip(
        self, files: list[tuple[str, bytes]], filename: str
    ) -> tuple[bytes, str]:
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for file_name, content in files:
                archive.writestr(file_name, content)
        return output.getvalue(), filename
