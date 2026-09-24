import hashlib
from base64 import b64decode
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.core import deps
from app.core.rate_limit import reset_rate_limiters
from app.main import app as fastapi_app
from app.models.kp_event import KpEvent
from app.models.user import User
from app.repositories.company_repository import CompanyRepository
from app.repositories.kp_repository import KpRepository
from app.repositories.mail_repository import MailTemplateRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.token_repository import TokenRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.invite_service import InviteService
from app.services.mail_service import MailService
from app.services.mail_template_service import MailTemplateService
from app.services.notification_recipients import NotificationRecipients
from app.services.storage_service import StorageService, StoredObject, UploadStream

CSRF_HEADER = "X-CSRF-Token"
DEFAULT_PASSWORD = "test-password-123"
MAX_QUANTITY_PER_BOOKING = 2
PNG_BYTES = b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)
PNG_UPLOAD = ("nametag.png", PNG_BYTES, "image/png")


@dataclass(frozen=True)
class KpSetup:
    event_id: str
    booth_zone_id: str
    service_id: str


async def move_event_into_the_past(db_session: AsyncSession, event_id: str) -> None:
    statement = select(KpEvent).where(col(KpEvent.id) == UUID(event_id))
    event = (await db_session.execute(statement)).scalar_one()
    today = date.today()
    event.registration_open = today - timedelta(days=40)
    event.registration_end = today - timedelta(days=30)
    event.finalization_deadline = today - timedelta(days=20)
    event.nametags_deadline = today - timedelta(days=10)
    event.event_date = today - timedelta(days=1)
    db_session.add(event)
    await db_session.commit()


def company_profile_payload(**overrides: object) -> dict[str, object]:
    return {
        "description": "We build the best anvils in Switzerland.",
        "general_email": "info@example.com",
        "billing_company_name": "Acme AG",
        "billing_street": "Invoice street",
        "billing_house_number": "1",
        "billing_postal_code": "8000",
        "billing_city": "Zurich",
        "billing_country": "CH",
        "billing_email": "billing@example.com",
        **overrides,
    }


async def first_member_id(client: AsyncClient, headers: dict[str, str]) -> str:
    members = await client.get("/api/company/me/members", headers=headers)
    return members.json()[0]["id"]


def kp_payload(name: str = "Kontaktparty") -> dict[str, str]:
    today = date.today()
    return {
        "name": name,
        "registration_open": str(today - timedelta(days=5)),
        "registration_end": str(today + timedelta(days=5)),
        "finalization_deadline": str(today + timedelta(days=6)),
        "nametags_deadline": str(today + timedelta(days=7)),
        "event_date": str(today + timedelta(days=30)),
    }


@pytest.fixture(autouse=True)
def clear_rate_limits() -> Iterator[None]:
    reset_rate_limiters()
    yield
    reset_rate_limiters()


@pytest.fixture
def mail_stub() -> AsyncMock:
    return AsyncMock()


async def _read_upload(upload: UploadStream, **_: object) -> bytes:
    return await upload.read()


async def _upload_bytes(
    *, key: str, content: bytes, filename: str, content_type: str
) -> StoredObject:
    return StoredObject(
        key=key,
        etag=f'"{filename}"',
        mime_type=content_type,
        size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
    )


@pytest.fixture
def storage_service() -> AsyncMock:
    service = AsyncMock(spec=StorageService)
    service.generate_download_url.return_value = "https://storage.test/download"
    service.download_bytes.return_value = PNG_BYTES
    service.read_upload.side_effect = _read_upload
    service.upload_bytes.side_effect = _upload_bytes
    service.validate_image_file.return_value = "image/png"
    service.validate_image_or_pdf_file.return_value = "image/png"
    service.validate_pdf_file.return_value = "application/pdf"
    service.validate_video_file.return_value = "video/mp4"
    service.validate_generic_file.return_value = "application/octet-stream"
    return service


@pytest.fixture
def mail_template_service(
    db_session: AsyncSession, mail_stub: AsyncMock
) -> MailTemplateService:
    return MailTemplateService(
        MailTemplateRepository(db_session),
        NotificationRecipients(KpRepository(db_session)),
        MailService(mail_stub),
    )


@pytest.fixture
def auth_service(
    db_session: AsyncSession, mail_template_service: MailTemplateService
) -> AuthService:
    return AuthService(
        UserRepository(db_session),
        TokenRepository(db_session),
        RoleRepository(db_session),
        mail_template_service,
        InviteService(CompanyRepository(db_session)),
    )


@pytest.fixture
def api_app(
    db_session: AsyncSession, mail_stub: AsyncMock, storage_service: AsyncMock
) -> Iterator[FastAPI]:
    async def override_db_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    async def override_stub() -> AsyncMock:
        return mail_stub

    def override_storage_service() -> AsyncMock:
        return storage_service

    fastapi_app.dependency_overrides[deps.get_db_session] = override_db_session
    fastapi_app.dependency_overrides[deps.get_stub] = override_stub
    fastapi_app.dependency_overrides[deps.get_storage_service] = (
        override_storage_service
    )
    yield fastapi_app
    fastapi_app.dependency_overrides.clear()


@pytest.fixture
async def client(api_app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=api_app), base_url="https://test"
    ) as client:
        yield client


@pytest.fixture
async def csrf_headers(client: AsyncClient) -> dict[str, str]:
    response = await client.get("/api/csrftoken")
    client.cookies.update(response.cookies)
    return {CSRF_HEADER: response.json()["token"]}


@pytest.fixture
def create_user(
    db_session: AsyncSession, auth_service: AuthService
) -> Callable[..., Awaitable[User]]:
    async def _create_user(
        *,
        email: str,
        password: str | None = DEFAULT_PASSWORD,
        first_name: str = "Test",
        last_name: str = "User",
        phone_number: str | None = None,
        is_staff: bool = False,
        is_admin: bool = False,
        is_company: bool = True,
        user_confirmed: bool = True,
        email_confirmed: bool = True,
        company_name: str | None = None,
        roles: Sequence[str] = (),
    ) -> User:
        company = (
            await CompanyRepository(db_session).create_company(company_name)
            if company_name is not None
            else None
        )
        role_repository = RoleRepository(db_session)
        user_roles = [await role_repository.get_or_create(name) for name in roles]
        user = User(
            email=email,
            password=await auth_service.hash_password(password) if password else None,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            is_staff=is_staff,
            is_admin=is_admin,
            is_company=is_company,
            user_confirmed=user_confirmed,
            email_confirmed=email_confirmed,
            company_id=company.id if company is not None else None,
        )
        return await UserRepository(db_session).create_user(user, user_roles)

    return _create_user


@pytest.fixture
async def company_user(create_user: Callable[..., Awaitable[User]]) -> User:
    return await create_user(email="company@example.com", company_name="Acme AG")


@pytest.fixture
async def staff_user(create_user: Callable[..., Awaitable[User]]) -> User:
    return await create_user(email="staff@example.com", is_staff=True, is_company=False)


@pytest.fixture
async def admin_user(create_user: Callable[..., Awaitable[User]]) -> User:
    return await create_user(
        email="admin@example.com", is_staff=True, is_admin=True, is_company=False
    )


@pytest.fixture
def auth_headers(
    auth_service: AuthService,
) -> Callable[[User], Awaitable[dict[str, str]]]:
    async def _auth_headers(user: User) -> dict[str, str]:
        token = await auth_service.create_access_token(user)
        return {"Authorization": f"Bearer {token}"}

    return _auth_headers


@pytest.fixture
async def staff_headers(
    admin_user: User,
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
) -> dict[str, str]:
    return {**await auth_headers(admin_user), **csrf_headers}


@pytest.fixture
async def company_headers(
    company_user: User,
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
) -> dict[str, str]:
    return {**await auth_headers(company_user), **csrf_headers}


@pytest.fixture
async def kp_setup(client: AsyncClient, staff_headers: dict[str, str]) -> KpSetup:
    event = await client.post(
        "/api/kp/create", json=kp_payload(), headers=staff_headers
    )
    event_id = event.json()["id"]
    booth_zone = await client.post(
        f"/api/kp/events/{event_id}/booth-zones",
        json={"name": "Main hall", "capacity": 5, "base_price": 10000},
        headers=staff_headers,
    )
    service = await client.post(
        f"/api/kp/events/{event_id}/services",
        json={
            "name": "Electricity",
            "price": 5000,
            "max_quantity_per_booking": MAX_QUANTITY_PER_BOOKING,
        },
        headers=staff_headers,
    )
    return KpSetup(
        event_id=event_id,
        booth_zone_id=booth_zone.json()["id"],
        service_id=service.json()["id"],
    )


@pytest.fixture
def complete_company_profile(
    client: AsyncClient,
) -> Callable[..., Awaitable[Response]]:
    async def _complete_company_profile(
        headers: dict[str, str], **overrides: object
    ) -> Response:
        return await client.put(
            "/api/company/me/profile",
            json=company_profile_payload(
                kp_contact_user_id=await first_member_id(client, headers),
                **overrides,
            ),
            headers=headers,
        )

    return _complete_company_profile


@pytest.fixture
def register_booking(
    client: AsyncClient,
    complete_company_profile: Callable[..., Awaitable[Response]],
) -> Callable[..., Awaitable[Response]]:
    async def _register_booking(
        headers: dict[str, str],
        kp_setup: KpSetup,
        quantity: int = 1,
    ) -> Response:
        await complete_company_profile(headers)
        return await client.post(
            f"/api/kp/events/{kp_setup.event_id}/bookings/register",
            json={
                "booth_zone_id": kp_setup.booth_zone_id,
                "services": [{"service_id": kp_setup.service_id, "quantity": quantity}],
                "confirm_profile": True,
            },
            headers=headers,
        )

    return _register_booking
