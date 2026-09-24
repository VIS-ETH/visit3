from collections.abc import Awaitable, Callable, Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute
from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.deps import get_current_user
from app.mail_templates.keys import MailTemplateKey
from app.main import app as fastapi_app
from app.models.industry import Industry
from app.models.kp_event import (
    KpEventBoothZone,
    KpEventService,
    KpEventServiceRequirement,
    KpEventServiceRequirementType,
    NameTag,
)
from app.models.user import User
from app.models.venue import KpVenueLayout
from app.repositories.company_repository import CompanyRepository
from tests.api.conftest import (
    PNG_UPLOAD,
    KpSetup,
    company_profile_payload,
    kp_payload,
)

KP_PRESIDENT_ROLE = get_settings().VISIT_KP_PRESIDENT_ROLE
INVITE_TOKEN = "matrix-invite-token"
MAIL_TEMPLATE_KEY = str(MailTemplateKey.PASSWORD_RESET)
INVITED_EMAIL = "invited@example.com"
REQUIREMENT_DESCRIPTION = "Upload the booth logo as a file."


class Persona(StrEnum):
    ANONYMOUS = "anonymous"
    UNCONFIRMED = "unconfirmed"
    COMPANY = "company"
    STAFF = "staff"
    PRESIDENT = "president"
    ADMIN = "admin"


class Access(StrEnum):
    AUTHENTICATED = "authenticated"
    COMPANY = "company"
    COMPANY_PROFILE = "company-profile"
    UNASSIGNED_COMPANY = "unassigned-company"
    STAFF = "staff"
    PRESIDENT = "president"
    ADMIN = "admin"


class Expected(StrEnum):
    UNAUTHENTICATED = "401"
    FORBIDDEN = "403"
    ALLOWED = "allowed"


PUBLIC_ROUTES = frozenset(
    {
        "GET /health",
        "GET /api/csrftoken",
        "POST /api/auth/register",
        "POST /api/auth/login",
        "POST /api/auth/refresh",
        "POST /api/auth/reset-password",
        "POST /api/auth/reset",
        "GET /api/auth/reset/{token}",
        "GET /api/auth/initiate",
        "GET /api/auth/link/{token}",
        "GET /api/auth/callback",
        "GET /api/user/confirm-email/{token}",
        "POST /api/user/confirm-email/{token}",
        "GET /api/company/invite/{token}",
    }
)

ROUTE_ACCESS: dict[str, Access] = {
    "GET /api/user/me": Access.AUTHENTICATED,
    "GET /api/user/profile": Access.AUTHENTICATED,
    "PATCH /api/user/me": Access.AUTHENTICATED,
    "POST /api/user/logout": Access.AUTHENTICATED,
    "POST /api/user/send-confirmation-email": Access.AUTHENTICATED,
    "GET /api/user/companies": Access.STAFF,
    "GET /api/user/admins": Access.STAFF,
    "GET /api/user/staff": Access.STAFF,
    "GET /api/user/unconfirmed": Access.STAFF,
    "GET /api/users": Access.STAFF,
    "GET /api/users/{user_id}": Access.STAFF,
    "POST /api/users/{user_id}/confirm": Access.STAFF,
    "POST /api/users/{user_id}/resend-confirmation": Access.STAFF,
    "PATCH /api/users/{user_id}": Access.STAFF,
    "DELETE /api/users/{user_id}": Access.STAFF,
    "POST /api/company/setup": Access.UNASSIGNED_COMPANY,
    "POST /api/company/invite/{token}/accept": Access.UNASSIGNED_COMPANY,
    "GET /api/company/me/members": Access.COMPANY,
    "GET /api/company/me": Access.COMPANY_PROFILE,
    "GET /api/company/me/profile": Access.COMPANY_PROFILE,
    "PUT /api/company/me/profile": Access.COMPANY_PROFILE,
    "POST /api/company/me/profile/logo": Access.COMPANY_PROFILE,
    "DELETE /api/company/me/profile/logo": Access.COMPANY_PROFILE,
    "GET /api/company/{company_id}/profile": Access.STAFF,
    "PUT /api/company/{company_id}/profile": Access.STAFF,
    "POST /api/company/{company_id}/profile/logo": Access.STAFF,
    "DELETE /api/company/{company_id}/profile/logo": Access.STAFF,
    "PATCH /api/company/me": Access.COMPANY,
    "POST /api/company/invite": Access.COMPANY,
    "GET /api/company/management/companies": Access.STAFF,
    "GET /api/company/{company_id}/users": Access.STAFF,
    "GET /api/company/{company_id}/with-users": Access.STAFF,
    "DELETE /api/company/{company_id}/delete-with-users": Access.ADMIN,
    "DELETE /api/company/{company_id}/delete-keep-users": Access.ADMIN,
    "GET /api/companies": Access.STAFF,
    "PATCH /api/companies/{company_id}": Access.STAFF,
    "POST /api/companies/{company_id}/members": Access.STAFF,
    "DELETE /api/companies/{company_id}/members/{user_id}": Access.STAFF,
    "GET /api/industries": Access.AUTHENTICATED,
    "POST /api/industries": Access.STAFF,
    "PATCH /api/industries/{industry_id}": Access.STAFF,
    "DELETE /api/industries/{industry_id}": Access.STAFF,
    "GET /api/kp/list": Access.AUTHENTICATED,
    "GET /api/kp/latest": Access.AUTHENTICATED,
    "GET /api/kp/events/{event_id}": Access.AUTHENTICATED,
    "GET /api/kp/events/{event_id}/settings": Access.PRESIDENT,
    "POST /api/kp/create": Access.PRESIDENT,
    "PATCH /api/kp/events/{event_id}": Access.PRESIDENT,
    "POST /api/kp/events/{event_id}/clone": Access.PRESIDENT,
    "GET /api/kp/events/{event_id}/booth-zones": Access.STAFF,
    "POST /api/kp/events/{event_id}/booth-zones": Access.PRESIDENT,
    "PATCH /api/kp/booth-zones/{booth_zone_id}": Access.PRESIDENT,
    "DELETE /api/kp/booth-zones/{booth_zone_id}": Access.PRESIDENT,
    "PUT /api/kp/booth-zones/{booth_zone_id}/layout-file": Access.PRESIDENT,
    "DELETE /api/kp/booth-zones/{booth_zone_id}/layout-file": Access.PRESIDENT,
    "GET /api/kp/events/{event_id}/services": Access.PRESIDENT,
    "POST /api/kp/events/{event_id}/services": Access.PRESIDENT,
    "PATCH /api/kp/services/{service_id}": Access.PRESIDENT,
    "DELETE /api/kp/services/{service_id}": Access.PRESIDENT,
    "POST /api/kp/services/{service_id}/image": Access.PRESIDENT,
    "DELETE /api/kp/services/{service_id}/image": Access.PRESIDENT,
    "GET /api/kp/events/{event_id}/venue-layouts": Access.PRESIDENT,
    "POST /api/kp/events/{event_id}/venue-layouts": Access.PRESIDENT,
    "PATCH /api/kp/venue-layouts/{layout_id}": Access.PRESIDENT,
    "DELETE /api/kp/venue-layouts/{layout_id}": Access.PRESIDENT,
    "PUT /api/kp/venue-layouts/{layout_id}/background": Access.PRESIDENT,
    "DELETE /api/kp/venue-layouts/{layout_id}/background": Access.PRESIDENT,
    "PUT /api/kp/venue-layouts/{layout_id}/shapes": Access.PRESIDENT,
    "PUT /api/kp/venue-layouts/{layout_id}/booths": Access.PRESIDENT,
    "GET /api/kp/events/{event_id}/venue": Access.AUTHENTICATED,
    "GET /api/kp/events/{event_id}/booth-zones/available": Access.COMPANY,
    "GET /api/kp/events/{event_id}/services/available": Access.COMPANY,
    "GET /api/kp/events/{event_id}/my-booking": Access.COMPANY,
    "POST /api/kp/events/{event_id}/bookings/register": Access.COMPANY,
    "POST /api/kp/bookings/{booking_id}/services": Access.COMPANY,
    "GET /api/kp/bookings/{booking_id}/upgrade-waitlist": Access.COMPANY,
    "PUT /api/kp/bookings/{booking_id}/upgrade-waitlist": Access.COMPANY,
    "POST /api/kp/bookings/{booking_id}/switch-zone": Access.COMPANY,
    "GET /api/kp/bookings/{booking_id}/nametags": Access.COMPANY,
    "PUT /api/kp/bookings/{booking_id}/nametags": Access.COMPANY,
    "GET /api/kp/staff/bookings/{booking_id}/nametags": Access.STAFF,
    "GET /api/kp/staff/bookings/{booking_id}/upgrade-waitlist": Access.STAFF,
    "PATCH /api/kp/bookings/{booking_id}/status": Access.COMPANY,
    "GET /api/kp/events/{event_id}/bookings": Access.STAFF,
    "GET /api/kp/events/{event_id}/bookings/{booking_id}": Access.STAFF,
    "PATCH /api/kp/bookings/{booking_id}/booth-number": Access.STAFF,
    "POST /api/kp/bookings/{booking_id}/accept": Access.STAFF,
    "POST /api/kp/bookings/{booking_id}/undo-accept": Access.STAFF,
    "POST /api/kp/bookings/{booking_id}/reject": Access.STAFF,
    "PATCH /api/kp/bookings/{booking_id}": Access.STAFF,
    "DELETE /api/kp/bookings/{booking_id}": Access.STAFF,
    "GET /api/kp/booking-services/{booking_service_id}/requirements/{requirement_id}/file": Access.COMPANY,
    "POST /api/kp/booking-services/{booking_service_id}/requirements/{requirement_id}/file": Access.COMPANY,
    "DELETE /api/kp/booking-services/{booking_service_id}/requirements/{requirement_id}/file": Access.COMPANY,
    "GET /api/kp/booking-services/{booking_service_id}/requirements/{requirement_id}/file/download": Access.COMPANY,
    "GET /api/kp/booking-services/{booking_service_id}/requirements/{requirement_id}/text": Access.COMPANY,
    "PUT /api/kp/booking-services/{booking_service_id}/requirements/{requirement_id}/text": Access.COMPANY,
    "GET /api/kp/staff/booking-services/{booking_service_id}/requirements/{requirement_id}/file": Access.STAFF,
    "GET /api/kp/staff/booking-services/{booking_service_id}/requirements/{requirement_id}/file/download": Access.STAFF,
    "GET /api/kp/staff/events/{event_id}/bookings/{booking_id}/requirement-files": Access.STAFF,
    "POST /api/kp/events/{event_id}/exports/nametags/background": Access.STAFF,
    "GET /api/kp/events/{event_id}/exports/nametags/background": Access.STAFF,
    "GET /api/kp/events/{event_id}/exports/nametags/targets": Access.STAFF,
    "GET /api/kp/events/{event_id}/exports/nametags/download": Access.STAFF,
    "GET /api/kp/bookings/{booking_id}/nametags/download": Access.STAFF,
    "GET /api/kp/nametags/{name_tag_id}/download": Access.STAFF,
    "GET /api/kp/events/{event_id}/exports/bookings/download": Access.STAFF,
    "GET /api/kp/events/{event_id}/exports/bookings/by-zone/download": Access.STAFF,
    "GET /api/kp/events/{event_id}/exports/waitlist-companies/download": Access.STAFF,
    "GET /api/kp/events/{event_id}/exports/booked-services/download": Access.STAFF,
    "GET /api/kp/events/{event_id}/exports/nametags-data/download": Access.STAFF,
    "GET /api/kp/events/{event_id}/exports/company-details/download": Access.STAFF,
    "GET /api/kp/events/{event_id}/exports/service-requirements/download": Access.STAFF,
    "GET /api/kp/events/{event_id}/exports/booth-zone-capacity/download": Access.STAFF,
    "GET /api/kp/events/{event_id}/exports/contacts/download": Access.STAFF,
    "GET /api/kp/events/{event_id}/exports/registration-exceptions/download": Access.STAFF,
    "GET /api/mail-templates": Access.STAFF,
    "GET /api/mail-templates/{key}": Access.STAFF,
    "PUT /api/mail-templates/{key}": Access.STAFF,
    "DELETE /api/mail-templates/{key}": Access.STAFF,
    "POST /api/mail-templates/{key}/preview": Access.STAFF,
    "POST /api/mail-templates/{key}/test-send": Access.STAFF,
}


class KpSubject(StrEnum):
    BOOKINGS = "bookings"
    EVENT_CONFIGURATION = "event-configuration"


SUBJECT_MINIMUM_ROLE: dict[KpSubject, Access] = {
    KpSubject.BOOKINGS: Access.STAFF,
    KpSubject.EVENT_CONFIGURATION: Access.PRESIDENT,
}

KP_ROUTE_SUBJECT: dict[str, KpSubject] = {
    "GET /api/kp/events/{event_id}/settings": KpSubject.EVENT_CONFIGURATION,
    "POST /api/kp/create": KpSubject.EVENT_CONFIGURATION,
    "PATCH /api/kp/events/{event_id}": KpSubject.EVENT_CONFIGURATION,
    "POST /api/kp/events/{event_id}/clone": KpSubject.EVENT_CONFIGURATION,
    "GET /api/kp/events/{event_id}/booth-zones": KpSubject.BOOKINGS,
    "POST /api/kp/events/{event_id}/booth-zones": KpSubject.EVENT_CONFIGURATION,
    "PATCH /api/kp/booth-zones/{booth_zone_id}": KpSubject.EVENT_CONFIGURATION,
    "DELETE /api/kp/booth-zones/{booth_zone_id}": KpSubject.EVENT_CONFIGURATION,
    "PUT /api/kp/booth-zones/{booth_zone_id}/layout-file": KpSubject.EVENT_CONFIGURATION,
    "DELETE /api/kp/booth-zones/{booth_zone_id}/layout-file": KpSubject.EVENT_CONFIGURATION,
    "GET /api/kp/events/{event_id}/services": KpSubject.EVENT_CONFIGURATION,
    "POST /api/kp/events/{event_id}/services": KpSubject.EVENT_CONFIGURATION,
    "PATCH /api/kp/services/{service_id}": KpSubject.EVENT_CONFIGURATION,
    "DELETE /api/kp/services/{service_id}": KpSubject.EVENT_CONFIGURATION,
    "POST /api/kp/services/{service_id}/image": KpSubject.EVENT_CONFIGURATION,
    "DELETE /api/kp/services/{service_id}/image": KpSubject.EVENT_CONFIGURATION,
    "GET /api/kp/events/{event_id}/venue-layouts": KpSubject.EVENT_CONFIGURATION,
    "POST /api/kp/events/{event_id}/venue-layouts": KpSubject.EVENT_CONFIGURATION,
    "PATCH /api/kp/venue-layouts/{layout_id}": KpSubject.EVENT_CONFIGURATION,
    "DELETE /api/kp/venue-layouts/{layout_id}": KpSubject.EVENT_CONFIGURATION,
    "PUT /api/kp/venue-layouts/{layout_id}/background": KpSubject.EVENT_CONFIGURATION,
    "DELETE /api/kp/venue-layouts/{layout_id}/background": KpSubject.EVENT_CONFIGURATION,
    "PUT /api/kp/venue-layouts/{layout_id}/shapes": KpSubject.EVENT_CONFIGURATION,
    "PUT /api/kp/venue-layouts/{layout_id}/booths": KpSubject.EVENT_CONFIGURATION,
    "GET /api/kp/events/{event_id}/bookings": KpSubject.BOOKINGS,
    "GET /api/kp/events/{event_id}/bookings/{booking_id}": KpSubject.BOOKINGS,
    "PATCH /api/kp/bookings/{booking_id}/booth-number": KpSubject.BOOKINGS,
    "POST /api/kp/bookings/{booking_id}/accept": KpSubject.BOOKINGS,
    "POST /api/kp/bookings/{booking_id}/undo-accept": KpSubject.BOOKINGS,
    "POST /api/kp/bookings/{booking_id}/reject": KpSubject.BOOKINGS,
    "PATCH /api/kp/bookings/{booking_id}": KpSubject.BOOKINGS,
    "DELETE /api/kp/bookings/{booking_id}": KpSubject.BOOKINGS,
    "GET /api/kp/staff/bookings/{booking_id}/nametags": KpSubject.BOOKINGS,
    "GET /api/kp/staff/bookings/{booking_id}/upgrade-waitlist": KpSubject.BOOKINGS,
    "GET /api/kp/staff/booking-services/{booking_service_id}/requirements/{requirement_id}/file": KpSubject.BOOKINGS,
    "GET /api/kp/staff/booking-services/{booking_service_id}/requirements/{requirement_id}/file/download": KpSubject.BOOKINGS,
    "GET /api/kp/staff/events/{event_id}/bookings/{booking_id}/requirement-files": KpSubject.BOOKINGS,
    "POST /api/kp/events/{event_id}/exports/nametags/background": KpSubject.BOOKINGS,
    "GET /api/kp/events/{event_id}/exports/nametags/background": KpSubject.BOOKINGS,
    "GET /api/kp/events/{event_id}/exports/nametags/targets": KpSubject.BOOKINGS,
    "GET /api/kp/events/{event_id}/exports/nametags/download": KpSubject.BOOKINGS,
    "GET /api/kp/bookings/{booking_id}/nametags/download": KpSubject.BOOKINGS,
    "GET /api/kp/nametags/{name_tag_id}/download": KpSubject.BOOKINGS,
    "GET /api/kp/events/{event_id}/exports/bookings/download": KpSubject.BOOKINGS,
    "GET /api/kp/events/{event_id}/exports/bookings/by-zone/download": KpSubject.BOOKINGS,
    "GET /api/kp/events/{event_id}/exports/waitlist-companies/download": KpSubject.BOOKINGS,
    "GET /api/kp/events/{event_id}/exports/booked-services/download": KpSubject.BOOKINGS,
    "GET /api/kp/events/{event_id}/exports/nametags-data/download": KpSubject.BOOKINGS,
    "GET /api/kp/events/{event_id}/exports/company-details/download": KpSubject.BOOKINGS,
    "GET /api/kp/events/{event_id}/exports/service-requirements/download": KpSubject.BOOKINGS,
    "GET /api/kp/events/{event_id}/exports/booth-zone-capacity/download": KpSubject.BOOKINGS,
    "GET /api/kp/events/{event_id}/exports/contacts/download": KpSubject.BOOKINGS,
    "GET /api/kp/events/{event_id}/exports/registration-exceptions/download": KpSubject.BOOKINGS,
}

REQUEST_BODIES: dict[str, dict[str, Any]] = {
    "PATCH /api/user/me": {},
    "PATCH /api/users/{user_id}": {},
    "POST /api/company/setup": {"name": "Matrix Holding {persona}"},
    "PATCH /api/company/me": {"name": "Matrix Holding {persona}"},
    "PATCH /api/companies/{company_id}": {"name": "Matrix Company {persona}"},
    "POST /api/companies/{company_id}/members": {"user_id": "{unassigned_user_id}"},
    "PUT /api/company/me/profile": company_profile_payload(),
    "PUT /api/company/{company_id}/profile": company_profile_payload(),
    "POST /api/industries": {"name": "Matrix catalogue {persona}"},
    "PATCH /api/industries/{industry_id}": {"name": "Matrix renamed {persona}"},
    "POST /api/company/invite": {"email": INVITED_EMAIL},
    "POST /api/kp/create": kp_payload("Matrix event {persona}"),
    "POST /api/kp/events/{event_id}/clone": kp_payload("Matrix clone {persona}"),
    "PATCH /api/kp/events/{event_id}": {},
    "POST /api/kp/events/{event_id}/booth-zones": {
        "name": "Matrix zone {persona}",
        "capacity": 1,
        "color": "{color}",
    },
    "PATCH /api/kp/booth-zones/{booth_zone_id}": {},
    "POST /api/kp/events/{event_id}/services": {"name": "Matrix service {persona}"},
    "PATCH /api/kp/services/{service_id}": {},
    "POST /api/kp/events/{event_id}/venue-layouts": {"name": "Matrix layout {persona}"},
    "PATCH /api/kp/venue-layouts/{layout_id}": {},
    "PUT /api/kp/venue-layouts/{layout_id}/shapes": {"shapes": []},
    "PUT /api/kp/venue-layouts/{layout_id}/booths": {"booths": []},
    "POST /api/kp/events/{event_id}/bookings/register": {
        "booth_zone_id": "{booth_zone_id}",
        "confirm_profile": True,
    },
    "POST /api/kp/bookings/{booking_id}/services": {"services": []},
    "PUT /api/kp/bookings/{booking_id}/upgrade-waitlist": {"target_booth_zone_ids": []},
    "PUT /api/kp/bookings/{booking_id}/nametags": {"name_tags": []},
    "POST /api/kp/bookings/{booking_id}/switch-zone": {
        "booth_zone_id": "{spare_booth_zone_id}"
    },
    "PATCH /api/kp/bookings/{booking_id}/status": {"status": "REGISTERED"},
    "PATCH /api/kp/bookings/{booking_id}/booth-number": {"booth_nr": 7},
    "PATCH /api/kp/bookings/{booking_id}": {},
    "POST /api/kp/bookings/{booking_id}/reject": {
        "reason": "The booth zone is no longer available for {persona}"
    },
    "PUT /api/kp/booking-services/{booking_service_id}/requirements/{requirement_id}/text": {
        "text_value": "answer"
    },
    "PUT /api/mail-templates/{key}": {
        "subject_de": "Betreff {persona}",
        "subject_en": "Subject {persona}",
        "body_de": "<p>Hallo</p>",
        "body_en": "<p>Hello</p>",
    },
}

UPLOAD_ROUTES = frozenset(
    {
        "POST /api/company/me/profile/logo",
        "POST /api/company/{company_id}/profile/logo",
        "POST /api/kp/services/{service_id}/image",
        "POST /api/kp/booking-services/{booking_service_id}/requirements/{requirement_id}/file",
        "POST /api/kp/events/{event_id}/exports/nametags/background",
        "PUT /api/kp/venue-layouts/{layout_id}/background",
        "PUT /api/kp/booth-zones/{booth_zone_id}/layout-file",
    }
)

PARAM_OVERRIDES: dict[str, dict[str, str]] = {
    "PATCH /api/industries/{industry_id}": {"industry_id": "catalogue_industry_id"},
    "DELETE /api/industries/{industry_id}": {"industry_id": "catalogue_industry_id"},
    "DELETE /api/kp/booth-zones/{booth_zone_id}": {
        "booth_zone_id": "spare_booth_zone_id"
    },
    "DELETE /api/kp/services/{service_id}": {"service_id": "spare_service_id"},
    "DELETE /api/kp/venue-layouts/{layout_id}": {"layout_id": "spare_layout_id"},
}


def _walk_routes(routes: list[Any], prefix: str) -> Iterator[tuple[str, APIRoute]]:
    for route in routes:
        included = getattr(route, "original_router", None)
        if included is not None:
            yield from _walk_routes(
                included.routes, prefix + route.include_context.prefix
            )
        elif isinstance(route, APIRoute):
            yield prefix, route


def api_routes(app: FastAPI) -> dict[str, APIRoute]:
    routes: dict[str, APIRoute] = {}
    for prefix, route in _walk_routes(app.routes, ""):
        for method in route.methods - {"HEAD", "OPTIONS"}:
            routes[f"{method} {prefix}{route.path}"] = route
    return routes


API_ROUTES = api_routes(fastapi_app)


def _authenticates(dependant: Dependant) -> bool:
    if dependant.call is get_current_user:
        return True
    return any(_authenticates(child) for child in dependant.dependencies)


def _expectations(allowed: set[Persona]) -> dict[Persona, Expected]:
    return {
        persona: Expected.UNAUTHENTICATED
        if persona is Persona.ANONYMOUS
        else Expected.ALLOWED
        if persona in allowed
        else Expected.FORBIDDEN
        for persona in Persona
    }


AUTHENTICATED_PERSONAS = {
    Persona.UNCONFIRMED,
    Persona.COMPANY,
    Persona.STAFF,
    Persona.PRESIDENT,
    Persona.ADMIN,
}
STAFF_PERSONAS = {Persona.STAFF, Persona.PRESIDENT, Persona.ADMIN}

EXPECTATIONS: dict[Access, dict[Persona, Expected]] = {
    Access.AUTHENTICATED: _expectations(AUTHENTICATED_PERSONAS),
    Access.COMPANY: _expectations({Persona.COMPANY}),
    Access.COMPANY_PROFILE: _expectations({Persona.COMPANY, Persona.UNCONFIRMED}),
    Access.UNASSIGNED_COMPANY: _expectations(set()),
    Access.STAFF: _expectations(STAFF_PERSONAS),
    Access.PRESIDENT: _expectations({Persona.PRESIDENT, Persona.ADMIN}),
    Access.ADMIN: _expectations({Persona.ADMIN}),
}

PERSONA_COLORS = {persona: f"#0000{index:02X}" for index, persona in enumerate(Persona)}


@dataclass(frozen=True)
class MatrixWorld:
    params: dict[str, str]
    headers: dict[Persona, dict[str, str]]


@pytest.fixture
async def admin_user(create_user: Callable[..., Awaitable[User]]) -> User:
    return await create_user(
        email="admin@example.com",
        password=None,
        is_staff=True,
        is_admin=True,
        is_company=False,
    )


@pytest.fixture
async def staff_user(create_user: Callable[..., Awaitable[User]]) -> User:
    return await create_user(
        email="staff@example.com", password=None, is_staff=True, is_company=False
    )


@pytest.fixture
async def president_user(create_user: Callable[..., Awaitable[User]]) -> User:
    return await create_user(
        email="president@example.com",
        password=None,
        is_staff=True,
        is_company=False,
        roles=(KP_PRESIDENT_ROLE,),
    )


@pytest.fixture
async def company_user(create_user: Callable[..., Awaitable[User]]) -> User:
    return await create_user(
        email="company@example.com", password=None, company_name="Acme AG"
    )


@pytest.fixture
async def unconfirmed_user(create_user: Callable[..., Awaitable[User]]) -> User:
    return await create_user(
        email="unconfirmed@example.com",
        password=None,
        user_confirmed=False,
        company_name="Unconfirmed AG",
    )


@pytest.fixture
async def unassigned_user(create_user: Callable[..., Awaitable[User]]) -> User:
    return await create_user(email="unassigned@example.com", password=None)


@pytest.fixture
async def matrix_headers(
    csrf_headers: dict[str, str],
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    unconfirmed_user: User,
    company_user: User,
    staff_user: User,
    president_user: User,
    admin_user: User,
) -> dict[Persona, dict[str, str]]:
    users = {
        Persona.UNCONFIRMED: unconfirmed_user,
        Persona.COMPANY: company_user,
        Persona.STAFF: staff_user,
        Persona.PRESIDENT: president_user,
        Persona.ADMIN: admin_user,
    }
    headers = {Persona.ANONYMOUS: dict(csrf_headers)}
    for persona, user in users.items():
        headers[persona] = {**await auth_headers(user), **csrf_headers}
    return headers


@pytest.fixture
async def matrix_world(
    client: AsyncClient,
    db_session: AsyncSession,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    company_user: User,
    unassigned_user: User,
    kp_setup: KpSetup,
    register_booking: Callable[..., Awaitable[Response]],
    matrix_headers: dict[Persona, dict[str, str]],
) -> MatrixWorld:
    booking = (await register_booking(company_headers, kp_setup)).json()
    requirement = KpEventServiceRequirement(
        service_id=UUID(kp_setup.service_id),
        type=KpEventServiceRequirementType.FILE,
        name="Booth logo",
        description=REQUIREMENT_DESCRIPTION,
    )
    name_tag = NameTag(
        booking_id=UUID(booking["id"]),
        first_name="Ada",
        last_name="Lovelace",
        position="Engineer",
    )
    spare_zone = KpEventBoothZone(
        event_id=UUID(kp_setup.event_id),
        name="Spare hall",
        description="",
        color="#FFEE00",
        capacity=1,
    )
    spare_service = KpEventService(
        event_id=UUID(kp_setup.event_id), name="Spare service", description=""
    )
    catalogue_industry = Industry(name="Catalogue software")
    layout = KpVenueLayout(event_id=UUID(kp_setup.event_id), name="Matrix layout")
    spare_layout = KpVenueLayout(event_id=UUID(kp_setup.event_id), name="Spare layout")
    db_session.add_all(
        [
            requirement,
            name_tag,
            spare_zone,
            spare_service,
            catalogue_industry,
            layout,
            spare_layout,
        ]
    )
    await db_session.commit()

    await CompanyRepository(db_session).create_invite(
        token=INVITE_TOKEN,
        company_id=UUID(str(company_user.company_id)),
        invited_email=INVITED_EMAIL,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )

    return MatrixWorld(
        params={
            "event_id": kp_setup.event_id,
            "booth_zone_id": kp_setup.booth_zone_id,
            "spare_booth_zone_id": str(spare_zone.id),
            "service_id": kp_setup.service_id,
            "spare_service_id": str(spare_service.id),
            "catalogue_industry_id": str(catalogue_industry.id),
            "layout_id": str(layout.id),
            "spare_layout_id": str(spare_layout.id),
            "booking_id": booking["id"],
            "booking_service_id": booking["services"][0]["id"],
            "requirement_id": str(requirement.id),
            "name_tag_id": str(name_tag.id),
            "company_id": str(company_user.company_id),
            "user_id": str(company_user.id),
            "unassigned_user_id": str(unassigned_user.id),
            "token": INVITE_TOKEN,
            "key": MAIL_TEMPLATE_KEY,
        },
        headers=matrix_headers,
    )


def _request_body(
    route_key: str, params: dict[str, str], persona: Persona
) -> dict[str, Any] | None:
    body = REQUEST_BODIES.get(route_key)
    if body is None:
        return None
    substitutions = {**params, "persona": persona, "color": PERSONA_COLORS[persona]}
    return {
        field: value.format(**substitutions) if isinstance(value, str) else value
        for field, value in body.items()
    }


async def call_route(
    client: AsyncClient, route_key: str, world: MatrixWorld, persona: Persona
) -> Response:
    method, path = route_key.split(" ", 1)
    overrides = {
        name: world.params[source]
        for name, source in PARAM_OVERRIDES.get(route_key, {}).items()
    }
    url = path.format(**{**world.params, **overrides})
    files = {"file": PNG_UPLOAD} if route_key in UPLOAD_ROUTES else None
    return await client.request(
        method,
        url,
        headers=world.headers[persona],
        json=_request_body(route_key, world.params, persona),
        files=files,
    )


def _outcome(response: Response) -> Expected:
    if response.status_code == 401:
        return Expected.UNAUTHENTICATED
    if response.status_code == 403:
        return Expected.FORBIDDEN
    return Expected.ALLOWED


def test_every_route_is_classified():
    assert set(API_ROUTES) == PUBLIC_ROUTES | set(ROUTE_ACCESS)


def _restricted_kp_routes() -> set[str]:
    minimum_roles = set(SUBJECT_MINIMUM_ROLE.values())
    return {
        route_key
        for route_key, access in ROUTE_ACCESS.items()
        if route_key.split(" ", 1)[1].startswith("/api/kp/") and access in minimum_roles
    }


def test_every_restricted_kp_route_has_a_subject():
    assert _restricted_kp_routes() == set(KP_ROUTE_SUBJECT)


def test_kp_routes_use_the_minimum_role_of_their_subject():
    assert {route_key: ROUTE_ACCESS[route_key] for route_key in KP_ROUTE_SUBJECT} == {
        route_key: SUBJECT_MINIMUM_ROLE[subject]
        for route_key, subject in KP_ROUTE_SUBJECT.items()
    }


def test_public_allowlist_matches_routes_without_authentication():
    unauthenticated = {
        route_key
        for route_key, route in API_ROUTES.items()
        if not _authenticates(route.dependant)
    }

    assert unauthenticated == PUBLIC_ROUTES


@pytest.mark.parametrize("route_key", sorted(ROUTE_ACCESS))
async def test_route_authorization(
    client: AsyncClient, matrix_world: MatrixWorld, route_key: str
):
    outcomes = {
        persona: _outcome(await call_route(client, route_key, matrix_world, persona))
        for persona in Persona
    }

    assert outcomes == EXPECTATIONS[ROUTE_ACCESS[route_key]]
