import csv
import io
import zipfile

from app.services.csv_service import CsvService


def test_render_csv_uses_given_field_order_and_ignores_extra_values():
    service = CsvService()

    content, filename = service.render_csv(
        [
            {"name": "Alice", "email": "alice@example.com", "ignored": "x"},
            {"name": "Bob", "email": "bob@example.com", "ignored": "y"},
        ],
        "users.csv",
        fieldnames=["email", "name"],
    )

    assert filename == "users.csv"
    rows = list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))
    assert rows == [
        {"email": "alice@example.com", "name": "Alice"},
        {"email": "bob@example.com", "name": "Bob"},
    ]


def test_render_csv_can_render_header_only_file():
    service = CsvService()

    content, filename = service.render_csv([], "empty.csv", fieldnames=["email"])

    assert filename == "empty.csv"
    assert content.decode("utf-8-sig") == "email\r\n"


def test_render_zip_contains_named_files():
    service = CsvService()

    content, filename = service.render_zip(
        [("one.txt", b"one"), ("nested/two.txt", b"two")],
        "export.zip",
    )

    assert filename == "export.zip"
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        assert archive.read("one.txt") == b"one"
        assert archive.read("nested/two.txt") == b"two"
