import asyncio
from collections.abc import Awaitable, Callable
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlmodel import col, func, select

from app.core.config import get_settings
from app.models.company import Company, CompanyInvite
from app.models.user import User
from app.repositories.company_repository import CompanyRepository
from app.repositories.user_repository import UserRepository

Sessions = async_sessionmaker[AsyncSession]
AuthHeaders = Callable[[User], Awaitable[dict[str, str]]]
PARALLEL = 8


async def make_company(sessions: Sessions, name: str) -> Company:
    async with sessions() as session:
        repository = CompanyRepository(session)
        return await repository.confirm_company(await repository.create_company(name))


async def add_member(sessions: Sessions, email: str, company_id: UUID) -> User:
    async with sessions() as session:
        return await UserRepository(session).create_user(
            User(
                email=email,
                first_name="Test",
                last_name="User",
                is_company=True,
                email_confirmed=True,
                company_id=company_id,
            )
        )


async def members(sessions: Sessions, company_id: UUID) -> int:
    async with sessions() as session:
        return await CompanyRepository(session).count_users(company_id)


async def count(sessions: Sessions, model: type, *conditions: object) -> int:
    async with sessions() as session:
        statement = select(func.count()).select_from(model).where(*conditions)
        return (await session.execute(statement)).scalar_one()


@pytest.fixture
def booked(monkeypatch: pytest.MonkeyPatch) -> None:
    async def has_bookings(self: CompanyRepository, company_id: UUID) -> bool:
        return True

    monkeypatch.setattr(
        CompanyRepository, "has_bookings_for_upcoming_events", has_bookings
    )


async def test_parallel_company_setups_leave_no_orphan_company(
    client: AsyncClient,
    create_user: Callable[..., Awaitable[User]],
    auth_headers: AuthHeaders,
    csrf_headers: dict[str, str],
    pg_sessionmaker: Sessions,
):
    founder = await create_user(email="founder@example.com")
    headers = {**await auth_headers(founder), **csrf_headers}

    responses = await asyncio.gather(
        *[
            client.post("/api/company/setup", json={"name": f"Co {i}"}, headers=headers)
            for i in range(PARALLEL)
        ]
    )

    assert [response.status_code for response in responses].count(200) == 1
    assert await count(pg_sessionmaker, Company) == 1


async def test_parallel_setups_of_one_name_create_one_company(
    client: AsyncClient,
    create_user: Callable[..., Awaitable[User]],
    auth_headers: AuthHeaders,
    csrf_headers: dict[str, str],
    pg_sessionmaker: Sessions,
):
    founders = [
        await create_user(email=f"founder{i}@example.com") for i in range(PARALLEL)
    ]

    responses = await asyncio.gather(
        *[
            client.post(
                "/api/company/setup",
                json={"name": "Twin AG"},
                headers={**await auth_headers(founder), **csrf_headers},
            )
            for founder in founders
        ]
    )

    codes = sorted(response.status_code for response in responses)
    assert codes == [200] + [409] * (PARALLEL - 1)
    assert await count(pg_sessionmaker, Company) == 1


async def test_parallel_renames_to_one_name_succeed_once(
    client: AsyncClient,
    staff_headers: dict[str, str],
    pg_sessionmaker: Sessions,
):
    companies = [
        await make_company(pg_sessionmaker, f"Original {i}") for i in range(PARALLEL)
    ]

    responses = await asyncio.gather(
        *[
            client.patch(
                f"/api/companies/{company.id}",
                json={"name": "Clash AG"},
                headers=staff_headers,
            )
            for company in companies
        ]
    )

    codes = sorted(response.status_code for response in responses)
    assert codes == [200] + [409] * (PARALLEL - 1)


@pytest.mark.usefixtures("booked")
async def test_parallel_member_removals_keep_a_booked_company_staffed(
    client: AsyncClient,
    staff_headers: dict[str, str],
    pg_sessionmaker: Sessions,
):
    for attempt in range(10):
        company = await make_company(pg_sessionmaker, f"Booked {attempt}")
        first = await add_member(pg_sessionmaker, f"a{attempt}@example.com", company.id)
        second = await add_member(
            pg_sessionmaker, f"b{attempt}@example.com", company.id
        )

        await asyncio.gather(
            *[
                client.delete(
                    f"/api/companies/{company.id}/members/{member.id}",
                    headers=staff_headers,
                )
                for member in (first, second)
            ]
        )

        assert await members(pg_sessionmaker, company.id) >= 1


@pytest.mark.usefixtures("booked")
async def test_parallel_account_deletions_keep_a_booked_company_staffed(
    client: AsyncClient,
    staff_headers: dict[str, str],
    pg_sessionmaker: Sessions,
):
    company = await make_company(pg_sessionmaker, "Booked AG")
    first = await add_member(pg_sessionmaker, "a@example.com", company.id)
    second = await add_member(pg_sessionmaker, "b@example.com", company.id)

    await asyncio.gather(
        *[
            client.delete(f"/api/users/{member.id}", headers=staff_headers)
            for member in (first, second)
        ]
    )

    assert await members(pg_sessionmaker, company.id) == 1


async def test_parallel_wrong_passwords_cannot_bypass_the_account_backoff(
    client: AsyncClient,
    create_user: Callable[..., Awaitable[User]],
    csrf_headers: dict[str, str],
):
    user = await create_user(email="victim@example.com")

    responses = await asyncio.gather(
        *[
            client.post(
                "/api/auth/login",
                data={"username": user.email, "password": f"wrong-{i}"},
                headers=csrf_headers,
            )
            for i in range(40)
        ]
    )

    codes = [response.status_code for response in responses]
    assert codes.count(400) <= get_settings().LOGIN_FAILURES_BEFORE_BACKOFF


async def test_parallel_registrations_with_one_email_create_one_account(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    pg_sessionmaker: Sessions,
):
    payload = {
        "email": "dup@example.com",
        "password": "brand-new-password",
        "first_name": "Ada",
        "last_name": "Lovelace",
    }

    await asyncio.gather(
        *[
            client.post("/api/auth/register", json=payload, headers=csrf_headers)
            for _ in range(4)
        ]
    )

    assert await count(pg_sessionmaker, User, col(User.email) == "dup@example.com") == 1


async def test_parallel_invites_of_one_email_create_one_invite(
    client: AsyncClient,
    company_headers: dict[str, str],
    pg_sessionmaker: Sessions,
):
    await asyncio.gather(
        *[
            client.post(
                "/api/company/invite",
                json={"email": "new@example.com"},
                headers=company_headers,
            )
            for _ in range(4)
        ]
    )

    assert await count(pg_sessionmaker, CompanyInvite) == 1


async def test_a_rename_during_a_confirmation_never_confirms_the_new_name(
    client: AsyncClient,
    staff_headers: dict[str, str],
    auth_headers: AuthHeaders,
    csrf_headers: dict[str, str],
    pg_sessionmaker: Sessions,
):
    for attempt in range(10):
        company = await make_company(pg_sessionmaker, f"Legit {attempt}")
        owner = await add_member(
            pg_sessionmaker, f"owner{attempt}@example.com", company.id
        )
        headers = {**await auth_headers(owner), **csrf_headers}
        renamed = await client.patch(
            "/api/company/me", json={"name": f"Reviewed {attempt}"}, headers=headers
        )
        assert renamed.status_code == 200, renamed.text

        await asyncio.gather(
            client.post(
                f"/api/companies/{company.id}/confirm",
                json={"name": f"Reviewed {attempt}"},
                headers=staff_headers,
            ),
            client.patch(
                "/api/company/me", json={"name": f"Evil {attempt}"}, headers=headers
            ),
        )

        async with pg_sessionmaker() as session:
            statement = select(Company).where(col(Company.id) == company.id)
            stored = (await session.execute(statement)).scalar_one()
        assert not (stored.confirmed_at is not None and stored.name.startswith("Evil"))
