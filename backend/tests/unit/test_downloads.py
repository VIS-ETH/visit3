from app.core.downloads import (
    content_disposition_attachment,
    sanitize_download_filename,
)
from app.routes.kp import _download


def test_sanitize_download_filename_removes_header_and_path_dangers():
    assert sanitize_download_filename('../"bad\r\nname.csv') == "badname.csv"
    assert sanitize_download_filename("/tmp/report.csv") == "tmp-report.csv"


def test_content_disposition_has_ascii_and_encoded_filename():
    header = content_disposition_attachment('Käpp/"report\r\n.csv')

    assert 'filename="Kapp-report.csv"' in header
    assert "filename*=UTF-8''K%C3%A4pp-report.csv" in header
    assert "\r" not in header
    assert "\n" not in header
    assert "/" not in header


def test_route_download_uses_safe_content_disposition_header():
    response = _download(b"content", 'Käpp/"report\r\n.csv', "text/csv")

    header = response.headers["content-disposition"]
    assert 'filename="Kapp-report.csv"' in header
    assert "filename*=UTF-8''K%C3%A4pp-report.csv" in header
    assert "\r" not in header
    assert "\n" not in header
