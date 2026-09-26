from collections.abc import Iterator
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import deps
from app.services.pdf_service import PdfService, RenderedImage
from tests.api.conftest import KpSetup, company_profile_payload
from tests.api.test_booklet_background_routes import preview_url

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class ConnectionProbePdfService(PdfService):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.held_during_render: list[bool] = []

    async def render_png(self, **kwargs: Any) -> RenderedImage:
        self.held_during_render.append(self.session.in_transaction())
        return RenderedImage(png=PNG_SIGNATURE, metadata=False)


@pytest.fixture
def probe(
    api_app: FastAPI, db_session: AsyncSession
) -> Iterator[ConnectionProbePdfService]:
    service = ConnectionProbePdfService(db_session)
    api_app.dependency_overrides[deps.get_pdf_service] = lambda: service
    yield service
    api_app.dependency_overrides.pop(deps.get_pdf_service, None)


async def test_a_company_preview_renders_without_holding_a_connection(
    client: AsyncClient,
    company_headers: dict[str, str],
    probe: ConnectionProbePdfService,
):
    response = await client.post(
        "/api/company/me/profile/booklet-page",
        json=company_profile_payload(),
        headers=company_headers,
    )

    assert response.status_code == 200
    assert probe.held_during_render == [False]


async def test_an_admin_sample_renders_without_holding_a_connection(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    probe: ConnectionProbePdfService,
):
    response = await client.post(preview_url(kp_setup.event_id), headers=staff_headers)

    assert response.status_code == 200
    assert probe.held_during_render == [False]
