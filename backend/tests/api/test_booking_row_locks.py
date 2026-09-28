from collections.abc import Awaitable, Callable
from uuid import UUID

import pytest
from httpx import AsyncClient, Response
from sqlalchemy.dialects import postgresql

from app.repositories.kp_repository import KpRepository
from tests.api.conftest import KpSetup


@pytest.fixture
def locked_bookings(monkeypatch: pytest.MonkeyPatch) -> list[UUID]:
    locked: list[UUID] = []
    original = KpRepository.lock_booking

    async def recording(self: KpRepository, booking_id: UUID):
        locked.append(booking_id)
        return await original(self, booking_id)

    monkeypatch.setattr(KpRepository, "lock_booking", recording)
    return locked


def test_the_booking_lock_is_a_row_lock_on_the_booking():
    statement = KpRepository.locked_booking_statement(
        UUID("00000000-0000-0000-0000-000000000001")
    )

    sql = str(statement.compile(dialect=postgresql.dialect()))

    assert "FOR UPDATE OF kpeventbooking" in sql


@pytest.mark.parametrize(
    ("method", "path", "body", "as_staff"),
    [
        ("POST", "accept", None, True),
        ("POST", "undo-accept", None, True),
        ("POST", "reject", {"reason": "The zone is already full."}, True),
        ("PATCH", "status", {"status": "CANCELLED"}, False),
        ("POST", "switch-zone", {"booth_zone_id": None}, False),
    ],
)
async def test_booking_state_changes_lock_the_booking_row(
    client: AsyncClient,
    kp_setup: KpSetup,
    company_headers: dict[str, str],
    staff_headers: dict[str, str],
    register_booking: Callable[..., Awaitable[Response]],
    locked_bookings: list[UUID],
    method: str,
    path: str,
    body: dict[str, object] | None,
    as_staff: bool,
):
    booking_id = (await register_booking(company_headers, kp_setup)).json()["id"]
    payload = (
        {**body, "booth_zone_id": kp_setup.booth_zone_id}
        if body and "booth_zone_id" in body
        else body
    )

    await client.request(
        method,
        f"/api/kp/bookings/{booking_id}/{path}",
        json=payload,
        headers=staff_headers if as_staff else company_headers,
    )

    assert UUID(booking_id) in locked_bookings
