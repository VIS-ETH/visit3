import csv
import io
import zipfile
from datetime import date, datetime
from uuid import UUID

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
        assert archive.read("nested-two.txt") == b"two"


def test_render_csv_escapes_formula_injection_values():
    service = CsvService()

    content, _ = service.render_csv(
        [
            {"value": "=cmd"},
            {"value": " +SUM(A1:A2)"},
            {"value": "@payload"},
            {"value": "\t=tab"},
            {"value": "\n=break"},
        ],
        "formula.csv",
        fieldnames=["value"],
    )

    rows = list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))
    assert [row["value"] for row in rows] == [
        "'=cmd",
        "' +SUM(A1:A2)",
        "'@payload",
        "'\t=tab",
        "'\n=break",
    ]


def test_render_csv_preserves_non_string_scalar_values():
    service = CsvService()
    entity_id = UUID("00000000-0000-0000-0000-000000000001")

    content, _ = service.render_csv(
        [
            {
                "count": 3,
                "active": True,
                "entity_id": entity_id,
                "day": date(2026, 5, 20),
                "created_at": datetime(2026, 5, 20, 12, 30),
            }
        ],
        "safe.csv",
        fieldnames=["count", "active", "entity_id", "day", "created_at"],
    )

    rows = list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))
    assert rows == [
        {
            "count": "3",
            "active": "True",
            "entity_id": str(entity_id),
            "day": "2026-05-20",
            "created_at": "2026-05-20 12:30:00",
        }
    ]


def test_render_csv_sanitizes_returned_filename():
    service = CsvService()

    _, filename = service.render_csv([], '../"bad\r\nname.csv', fieldnames=["value"])

    assert filename == "badname.csv"


def test_render_zip_sanitizes_member_names_and_filename():
    service = CsvService()

    content, filename = service.render_zip(
        [
            ("../x.csv", b"x"),
            ("/tmp/y.csv", b"y"),
            ("bad\r\nname.csv", b"z"),
        ],
        '../"export\r.zip',
    )

    assert filename == "export.zip"
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        assert sorted(archive.namelist()) == ["badname.csv", "tmp-y.csv", "x.csv"]
