import pytest

from app.services.pdf_service import PdfService, PdfUnreadable
from app.services.typst_runner import TypstRenderAborted
from tests.booklet_pdfs import make_pdf


async def test_an_a5_page_reports_its_size():
    page = await PdfService().inspect_pdf(make_pdf())

    assert page.width_mm == pytest.approx(148, abs=0.5)
    assert page.height_mm == pytest.approx(210, abs=0.5)
    assert page.has_more_pages is False


async def test_an_a4_page_reports_its_size():
    page = await PdfService().inspect_pdf(make_pdf(210, 297))

    assert page.width_mm == pytest.approx(210, abs=0.5)
    assert page.height_mm == pytest.approx(297, abs=0.5)


async def test_a_second_page_is_detected():
    page = await PdfService().inspect_pdf(make_pdf(pages=2))

    assert page.has_more_pages is True


async def test_a_corrupt_pdf_is_unreadable():
    with pytest.raises(PdfUnreadable):
        await PdfService().inspect_pdf(b"%PDF-1.7\nnot really a pdf")


async def test_a_probe_over_its_limit_is_aborted():
    with pytest.raises(TypstRenderAborted):
        await PdfService().inspect_pdf(make_pdf(), timeout=0.001)
