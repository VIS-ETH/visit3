from __future__ import annotations

import asyncio
import hashlib
import random
import struct
import sys
import zlib
from collections.abc import Mapping
from datetime import date
from pathlib import Path
from typing import TypedDict

from pwdlib import PasswordHash
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import col, select

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings
from app.models.company import Company
from app.models.kp_event import (
    KpBookingCompanyDetails,
    KpBookingCompanyDetailsIndustryLink,
    KpBookingStatus,
    KpCompanyLanguage,
    KpEvent,
    KpEventBooking,
    KpEventBookingService,
    KpEventBookingServiceFileLink,
    KpEventBoothZone,
    KpEventBoothZoneServiceLink,
    KpEventNametagBackground,
    KpEventService,
    KpEventServiceRequirement,
    KpEventServiceRequirementType,
    KpIndustry,
    NameTag,
)
from app.models.storage import StoredFile
from app.models.user import User
from app.services.storage_service import StorageService

password_hash = PasswordHash.recommended()
SEED_USER_PASSWORD = "12345678901"


class KpExportCompanySeed(TypedDict):
    name: str
    zone: str
    booth_nr: int
    nametags: list[tuple[str, str, str]]


class BoothZoneSeed(TypedDict):
    description: str
    color: str
    order: int
    capacity: int
    booth_size: float
    base_price: int


class ServiceRequirementSeed(TypedDict):
    type: KpEventServiceRequirementType
    name: str
    description: str
    order: int


class ServiceSeed(TypedDict):
    description: str
    confirmation_description: str
    order: int
    price: int
    max_quantity_per_booking: int
    max_total_quantity: int
    is_active: bool
    requirements: list[ServiceRequirementSeed]


class BookingServiceSeed(TypedDict):
    quantity: int
    included_quantity: int
    text_answers: dict[str, str]


class CompanyDetailsSeed(TypedDict):
    profile: str
    brand_name: str
    address: str
    contact_person: str
    places_of_work: str
    employees_count: int
    employees_count_switzerland: int
    offer_internship: bool
    offer_part_time: bool
    offer_thesis: bool
    languages: list[KpCompanyLanguage]
    industries: list[str]


class DummyFileSeed(TypedDict):
    storage_key: str
    filename: str
    content_type: str
    content: bytes


class SeedUser(TypedDict):
    email: str
    first_name: str
    last_name: str
    is_admin: bool
    is_staff: bool
    is_company: bool
    user_confirmed: bool
    email_confirmed: bool
    company_key: str | None


class SeedUserFlags(TypedDict):
    is_admin: bool
    is_staff: bool
    is_company: bool
    user_confirmed: bool
    email_confirmed: bool


SEED_COMPANIES = {
    "seed-vendor": "Seed Vendor AG",
    "seed-partner": "Seed Partner GmbH",
    "seed-robotics": "Seed Robotics AG",
}

KP_EVENT_NAME = "Kontaktparty Nametag Export Test"
KP_BACKGROUND_STORAGE_KEY = "seed/nametag-export-test/background.png"

DUMMY_DEVICE_SPEC_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 144]"
    b"/Contents 4 0 R/Resources<<>>>>endobj\n"
    b"4 0 obj<</Length 58>>stream\n"
    b"BT /F1 12 Tf 36 100 Td (Seed dummy device specification) Tj ET\n"
    b"endstream endobj\n"
    b"trailer<</Root 1 0 R>>\n%%EOF\n"
)

DUMMY_SHIPPING_LABEL = (
    b"Seed Freight Handling\n"
    b"Recipient: Kontaktparty Logistics Desk\n"
    b"Reference: Seed Robotics AG booth 11\n"
    b"Tracking: SEED-TRACK-0001\n"
)

KP_EXPORT_COMPANIES: list[KpExportCompanySeed] = [
    {
        "name": "Seed Robotics AG",
        "zone": "Main Hall",
        "booth_nr": 11,
        "nametags": [
            ("Ada", "Lovelace", "Software Engineer"),
            ("Grace", "Hopper", "Compiler Specialist"),
            ("Linus", "Torvalds", "Platform Engineer"),
        ],
    },
    {
        "name": "Seed Quantum GmbH",
        "zone": "Main Hall",
        "booth_nr": 12,
        "nametags": [
            ("Katherine", "Johnson", "Research Scientist"),
            ("Alan", "Turing", "Cryptography Lead"),
        ],
    },
    {
        "name": "Seed Interfaces SA",
        "zone": "Startup Alley",
        "booth_nr": 3,
        "nametags": [
            ("Margaret", "Hamilton", "Systems Architect"),
            ("Donald", "Knuth", "Algorithm Designer"),
            ("Barbara", "Liskov", "Principal Engineer"),
            ("Edsger", "Dijkstra", "Formal Methods Lead"),
        ],
    },
]

KP_EXPORT_ZONES: dict[str, BoothZoneSeed] = {
    "Main Hall": {
        "description": "Primary seed zone for nametag export testing.",
        "color": "#1F7A5C",
        "order": 10,
        "capacity": 50,
        "booth_size": 12.0,
        "base_price": 120000,
    },
    "Startup Alley": {
        "description": "Secondary seed zone for smaller company booths.",
        "color": "#355C9A",
        "order": 20,
        "capacity": 20,
        "booth_size": 8.0,
        "base_price": 75000,
    },
}

KP_EXPORT_SERVICES: dict[str, ServiceSeed] = {
    "Power Connection": {
        "description": "Dedicated 230V booth power with cable routing prepared before the event.",
        "confirmation_description": "The event operations team will confirm the connection point during booth setup.",
        "order": 10,
        "price": 15000,
        "max_quantity_per_booking": 4,
        "max_total_quantity": 80,
        "is_active": True,
        "requirements": [
            {
                "type": KpEventServiceRequirementType.TEXT,
                "name": "Power usage",
                "description": "Describe the devices you plan to connect and their approximate total power draw.",
                "order": 10,
            },
            {
                "type": KpEventServiceRequirementType.PDF,
                "name": "Device specification",
                "description": "Upload a device specification PDF if your setup includes specialized hardware.",
                "order": 20,
            },
        ],
    },
    "WLAN Voucher Pack": {
        "description": "Additional Wi-Fi vouchers for booth representatives and demo devices.",
        "confirmation_description": "Voucher codes will be sent to the primary company contact shortly before the event.",
        "order": 20,
        "price": 2500,
        "max_quantity_per_booking": 10,
        "max_total_quantity": 200,
        "is_active": True,
        "requirements": [
            {
                "type": KpEventServiceRequirementType.TEXT,
                "name": "Voucher recipients",
                "description": "List recipient names or device labels that should receive dedicated WLAN vouchers.",
                "order": 10,
            },
        ],
    },
    "Freight Handling": {
        "description": "Receiving, temporary storage, and delivery of shipped booth material.",
        "confirmation_description": "Use the shipping label instructions shown after booking this service.",
        "order": 30,
        "price": 8000,
        "max_quantity_per_booking": 3,
        "max_total_quantity": 30,
        "is_active": True,
        "requirements": [
            {
                "type": KpEventServiceRequirementType.TEXT,
                "name": "Package count",
                "description": "Provide the expected number of boxes and the approximate delivery window.",
                "order": 10,
            },
            {
                "type": KpEventServiceRequirementType.FILE,
                "name": "Shipping label",
                "description": "Upload the shipping label or tracking document for incoming freight.",
                "order": 20,
            },
        ],
    },
    "Sponsor Screen Slot": {
        "description": "A rotating slide on the venue screens during breaks and arrival windows.",
        "confirmation_description": "Slides are reviewed by the Kontaktparty team before publication.",
        "order": 40,
        "price": 12000,
        "max_quantity_per_booking": 2,
        "max_total_quantity": 12,
        "is_active": True,
        "requirements": [
            {
                "type": KpEventServiceRequirementType.IMAGE,
                "name": "Screen artwork",
                "description": "Upload a landscape image that can be displayed on the venue screens.",
                "order": 10,
            },
            {
                "type": KpEventServiceRequirementType.TEXT,
                "name": "Slide caption",
                "description": "Provide the short caption that should accompany the sponsor screen slide.",
                "order": 20,
            },
        ],
    },
    "Legacy Brochure Stand": {
        "description": "Inactive example service kept for testing admin visibility and old bookings.",
        "confirmation_description": "This legacy service is no longer offered for new bookings.",
        "order": 90,
        "price": 5000,
        "max_quantity_per_booking": 1,
        "max_total_quantity": 0,
        "is_active": False,
        "requirements": [],
    },
}

KP_SERVICE_IMAGE_FILES: dict[str, DummyFileSeed] = {
    "Power Connection": {
        "storage_key": "seed/nametag-export-test/services/power-connection.png",
        "filename": "seed-service-power.png",
        "content_type": "image/png",
        "content": b"",
    },
    "WLAN Voucher Pack": {
        "storage_key": "seed/nametag-export-test/services/wlan-vouchers.png",
        "filename": "seed-service-wlan.png",
        "content_type": "image/png",
        "content": b"",
    },
    "Freight Handling": {
        "storage_key": "seed/nametag-export-test/services/freight-handling.png",
        "filename": "seed-service-freight.png",
        "content_type": "image/png",
        "content": b"",
    },
    "Sponsor Screen Slot": {
        "storage_key": "seed/nametag-export-test/services/sponsor-screen.png",
        "filename": "seed-service-sponsor-screen.png",
        "content_type": "image/png",
        "content": b"",
    },
}

KP_ZONE_INCLUDED_SERVICES: dict[str, dict[str, int]] = {
    "Main Hall": {
        "Power Connection": 1,
        "WLAN Voucher Pack": 2,
    },
    "Startup Alley": {
        "WLAN Voucher Pack": 1,
    },
}

KP_REQUIREMENT_FILE_ANSWERS: dict[str, dict[str, dict[str, DummyFileSeed]]] = {
    "Seed Robotics AG": {
        "Power Connection": {
            "Device specification": {
                "storage_key": "seed/nametag-export-test/requirements/seed-robotics-device-spec.pdf",
                "filename": "seed-robotics-device-spec.pdf",
                "content_type": "application/pdf",
                "content": DUMMY_DEVICE_SPEC_PDF,
            },
        },
        "Freight Handling": {
            "Shipping label": {
                "storage_key": "seed/nametag-export-test/requirements/seed-robotics-shipping-label.txt",
                "filename": "seed-robotics-shipping-label.txt",
                "content_type": "text/plain",
                "content": DUMMY_SHIPPING_LABEL,
            },
        },
    },
    "Seed Quantum GmbH": {
        "Sponsor Screen Slot": {
            "Screen artwork": {
                "storage_key": "seed/nametag-export-test/requirements/seed-quantum-screen-artwork.png",
                "filename": "seed-quantum-screen-artwork.png",
                "content_type": "image/png",
                "content": b"",
            },
        },
    },
}

KP_BOOKING_SERVICES: dict[str, dict[str, BookingServiceSeed]] = {
    "Seed Robotics AG": {
        "Power Connection": {
            "quantity": 3,
            "included_quantity": 1,
            "text_answers": {
                "Power usage": "Two demo robots, one laptop dock, and one 27 inch display. Expected peak draw is about 1.2 kW.",
            },
        },
        "WLAN Voucher Pack": {
            "quantity": 4,
            "included_quantity": 2,
            "text_answers": {
                "Voucher recipients": "Ada Lovelace, Grace Hopper, Linus Torvalds, demo-robot-01.",
            },
        },
        "Freight Handling": {
            "quantity": 1,
            "included_quantity": 0,
            "text_answers": {
                "Package count": "Three boxes arriving by courier on the morning before the event.",
            },
        },
    },
    "Seed Quantum GmbH": {
        "Power Connection": {
            "quantity": 1,
            "included_quantity": 1,
            "text_answers": {
                "Power usage": "Laptop demos and one low-power measurement display, below 300 W total.",
            },
        },
        "Sponsor Screen Slot": {
            "quantity": 1,
            "included_quantity": 0,
            "text_answers": {
                "Slide caption": "Meet Seed Quantum at booth 12 for quantum software internships.",
            },
        },
    },
    "Seed Interfaces SA": {
        "WLAN Voucher Pack": {
            "quantity": 3,
            "included_quantity": 1,
            "text_answers": {
                "Voucher recipients": "Margaret Hamilton, Donald Knuth, Barbara Liskov.",
            },
        },
        "Legacy Brochure Stand": {
            "quantity": 1,
            "included_quantity": 0,
            "text_answers": {},
        },
    },
}

KP_COMPANY_DETAILS: dict[str, CompanyDetailsSeed] = {
    "Seed Robotics AG": {
        "profile": "Seed Robotics builds autonomous inspection robots for industrial facilities.",
        "brand_name": "Seed Robotics",
        "address": "Technoparkstrasse 1, 8005 Zurich",
        "contact_person": "Ada Lovelace",
        "places_of_work": "Zurich, Winterthur, remote hybrid",
        "employees_count": 180,
        "employees_count_switzerland": 95,
        "offer_internship": True,
        "offer_part_time": True,
        "offer_thesis": True,
        "languages": [KpCompanyLanguage.ENGLISH, KpCompanyLanguage.GERMAN],
        "industries": ["Robotics", "Industrial Automation", "Software"],
    },
    "Seed Quantum GmbH": {
        "profile": "Seed Quantum develops simulation and optimization tools for engineering teams.",
        "brand_name": "Seed Quantum",
        "address": "Europaallee 20, 8004 Zurich",
        "contact_person": "Katherine Johnson",
        "places_of_work": "Zurich, Basel",
        "employees_count": 64,
        "employees_count_switzerland": 42,
        "offer_internship": True,
        "offer_part_time": False,
        "offer_thesis": True,
        "languages": [KpCompanyLanguage.ENGLISH],
        "industries": ["Quantum Computing", "Software"],
    },
    "Seed Interfaces SA": {
        "profile": "Seed Interfaces designs embedded UI systems for medical and lab equipment.",
        "brand_name": "Seed Interfaces",
        "address": "Rue du Rhone 15, 1204 Geneva",
        "contact_person": "Margaret Hamilton",
        "places_of_work": "Geneva, Lausanne, Zurich",
        "employees_count": 92,
        "employees_count_switzerland": 88,
        "offer_internship": True,
        "offer_part_time": True,
        "offer_thesis": False,
        "languages": [
            KpCompanyLanguage.ENGLISH,
            KpCompanyLanguage.FRENCH,
            KpCompanyLanguage.GERMAN,
        ],
        "industries": ["Human Computer Interaction", "Embedded Systems"],
    },
}

RANDOM_SEED = 20260217

FIRST_NAMES = [
    "Ada",
    "Noah",
    "Mia",
    "Luca",
    "Nora",
    "Emil",
    "Lea",
    "Jonas",
    "Lina",
    "Felix",
    "Sofia",
    "David",
    "Emma",
    "Elias",
    "Mila",
    "Simon",
    "Jana",
    "Leo",
    "Nina",
    "Tim",
    "Sara",
    "Paul",
    "Clara",
    "Oskar",
    "Iris",
    "Roman",
    "Laura",
    "Ben",
    "Tina",
    "Kai",
]

LAST_NAMES = [
    "Meyer",
    "Schmidt",
    "Keller",
    "Fischer",
    "Wagner",
    "Weber",
    "Huber",
    "Koch",
    "Bauer",
    "Zimmermann",
    "Braun",
    "Hartmann",
    "Kruger",
    "Neumann",
    "Schulz",
    "Maier",
    "Becker",
    "Wolf",
    "Lang",
    "Klein",
    "Roth",
    "Krause",
    "Seidel",
    "Winter",
    "Peters",
    "Franke",
    "Jager",
    "Frei",
    "Graf",
    "Vogel",
]

EMAIL_POOL = [
    "atlas.user01@test.local",
    "atlas.user02@test.local",
    "atlas.user03@test.local",
    "atlas.user04@test.local",
    "atlas.user05@test.local",
    "atlas.user06@test.local",
    "atlas.user07@test.local",
    "atlas.user08@test.local",
    "atlas.user09@test.local",
    "atlas.user10@test.local",
    "nova.user11@test.local",
    "nova.user12@test.local",
    "nova.user13@test.local",
    "nova.user14@test.local",
    "nova.user15@test.local",
    "nova.user16@test.local",
    "nova.user17@test.local",
    "nova.user18@test.local",
    "nova.user19@test.local",
    "nova.user20@test.local",
    "terra.user21@test.local",
    "terra.user22@test.local",
    "terra.user23@test.local",
    "terra.user24@test.local",
    "terra.user25@test.local",
    "terra.user26@test.local",
    "terra.user27@test.local",
    "terra.user28@test.local",
    "terra.user29@test.local",
    "terra.user30@test.local",
    "orbit.user31@test.local",
    "orbit.user32@test.local",
    "orbit.user33@test.local",
    "orbit.user34@test.local",
    "orbit.user35@test.local",
    "orbit.user36@test.local",
    "orbit.user37@test.local",
    "orbit.user38@test.local",
    "orbit.user39@test.local",
    "orbit.user40@test.local",
    "pulse.user41@test.local",
    "pulse.user42@test.local",
    "pulse.user43@test.local",
    "pulse.user44@test.local",
    "pulse.user45@test.local",
    "pulse.user46@test.local",
    "pulse.user47@test.local",
    "pulse.user48@test.local",
]

SEED_USER_COUNTS = {
    "unconfirmed": 12,
    "staff": 12,
    "admins": 8,
    "company": 12,
}

KNOWN_COMPANY_USERS: list[SeedUser] = [
    {
        "email": "seed.company@test.local",
        "first_name": "Seed",
        "last_name": "Company",
        "is_admin": False,
        "is_staff": False,
        "is_company": True,
        "user_confirmed": True,
        "email_confirmed": True,
        "company_key": "seed-robotics",
    },
]


def generate_seed_users() -> list[SeedUser]:
    randomizer = random.Random(RANDOM_SEED)
    shuffled_emails = EMAIL_POOL.copy()
    randomizer.shuffle(shuffled_emails)

    total_needed = sum(SEED_USER_COUNTS.values())
    if total_needed > len(shuffled_emails):
        raise ValueError(
            f"Not enough emails in EMAIL_POOL: need {total_needed}, have {len(shuffled_emails)}"
        )

    users: list[SeedUser] = []
    company_keys = list(SEED_COMPANIES.keys())
    email_index = 0

    for group, count in SEED_USER_COUNTS.items():
        for _ in range(count):
            email = shuffled_emails[email_index]
            email_index += 1

            first_name = randomizer.choice(FIRST_NAMES)
            last_name = randomizer.choice(LAST_NAMES)

            if group == "unconfirmed":
                user_payload: SeedUserFlags = {
                    "is_admin": False,
                    "is_staff": False,
                    "is_company": True,
                    "user_confirmed": False,
                    "email_confirmed": randomizer.choice([True, False]),
                }
            elif group == "staff":
                user_payload = {
                    "is_admin": False,
                    "is_staff": True,
                    "is_company": False,
                    "user_confirmed": True,
                    "email_confirmed": True,
                }
            elif group == "admins":
                user_payload = {
                    "is_admin": True,
                    "is_staff": False,
                    "is_company": False,
                    "user_confirmed": True,
                    "email_confirmed": True,
                }
            else:
                user_payload = {
                    "is_admin": False,
                    "is_staff": False,
                    "is_company": True,
                    "user_confirmed": True,
                    "email_confirmed": True,
                }

            users.append(
                {
                    "email": email,
                    "first_name": first_name,
                    "last_name": last_name,
                    "is_admin": user_payload["is_admin"],
                    "is_staff": user_payload["is_staff"],
                    "is_company": user_payload["is_company"],
                    "user_confirmed": user_payload["user_confirmed"],
                    "email_confirmed": user_payload["email_confirmed"],
                    "company_key": randomizer.choice(company_keys)
                    if user_payload["is_company"]
                    else None,
                }
            )

    return users


def png_chunk(kind: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + kind
        + data
        + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    )


def make_background_png(width: int = 900, height: int = 540) -> bytes:
    rows: list[bytes] = []
    for y in range(height):
        row = bytearray()
        for x in range(width):
            in_border = x < 18 or x >= width - 18 or y < 18 or y >= height - 18
            in_line = 350 <= y <= 360 or 425 <= y <= 432
            if in_border:
                row.extend((31, 122, 92))
            elif in_line:
                row.extend((210, 226, 220))
            else:
                shade = 248 - ((x + y) % 8)
                row.extend((shade, shade, 244))
        rows.append(b"\x00" + bytes(row))

    raw = b"".join(rows)
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", header)
        + png_chunk(b"IDAT", zlib.compress(raw, level=9))
        + png_chunk(b"IEND", b"")
    )


async def get_or_create_company(session, name: str) -> Company:
    company = (
        await session.execute(select(Company).where(Company.name == name))
    ).scalar_one_or_none()
    if company:
        return company

    company = Company(name=name)
    session.add(company)
    await session.flush()
    return company


async def get_or_create_kp_event(session) -> KpEvent:
    event = (
        await session.execute(select(KpEvent).where(KpEvent.name == KP_EVENT_NAME))
    ).scalar_one_or_none()
    if event:
        return event

    event = KpEvent(
        name=KP_EVENT_NAME,
        registration_open=date(2026, 1, 15),
        registration_end=date(2026, 3, 31),
        finalization_deadline=date(2026, 4, 15),
        nametags_deadline=date(2026, 4, 30),
        event_date=date(2026, 5, 15),
    )
    session.add(event)
    await session.flush()
    return event


async def get_or_create_booth_zone(
    session, event: KpEvent, name: str, values: Mapping[str, object]
) -> KpEventBoothZone:
    zone = (
        await session.execute(
            select(KpEventBoothZone).where(
                KpEventBoothZone.event_id == event.id,
                KpEventBoothZone.name == name,
            )
        )
    ).scalar_one_or_none()

    if zone is None:
        zone = KpEventBoothZone(event_id=event.id, name=name, **values)
    else:
        for key, value in values.items():
            setattr(zone, key, value)

    session.add(zone)
    await session.flush()
    return zone


async def get_or_create_booking(
    session,
    event: KpEvent,
    company: Company,
    zone: KpEventBoothZone,
    booth_nr: int,
) -> KpEventBooking:
    booking = (
        await session.execute(
            select(KpEventBooking).where(
                KpEventBooking.event_id == event.id,
                KpEventBooking.company_id == company.id,
                KpEventBooking.booth_zone_id == zone.id,
            )
        )
    ).scalar_one_or_none()

    if booking is None:
        booking = KpEventBooking(
            event_id=event.id,
            company_id=company.id,
            booth_zone_id=zone.id,
            booth_nr=booth_nr,
            status=KpBookingStatus.CONFIRMED,
        )
    else:
        booking.booth_nr = booth_nr
        booking.status = KpBookingStatus.CONFIRMED

    session.add(booking)
    await session.flush()
    return booking


async def get_or_create_service(
    session,
    event: KpEvent,
    name: str,
    values: ServiceSeed,
) -> tuple[KpEventService, dict[str, KpEventServiceRequirement]]:
    service = (
        await session.execute(
            select(KpEventService).where(
                KpEventService.event_id == event.id,
                KpEventService.name == name,
            )
        )
    ).scalar_one_or_none()

    service_values = {
        key: value for key, value in values.items() if key != "requirements"
    }
    if service is None:
        service = KpEventService(event_id=event.id, name=name, **service_values)
    else:
        for key, value in service_values.items():
            setattr(service, key, value)

    session.add(service)
    await session.flush()

    existing_requirements = (
        (
            await session.execute(
                select(KpEventServiceRequirement).where(
                    KpEventServiceRequirement.service_id == service.id
                )
            )
        )
        .scalars()
        .all()
    )
    requirements_by_name = {
        requirement.name: requirement for requirement in existing_requirements
    }

    for requirement_seed in values["requirements"]:
        requirement = requirements_by_name.get(requirement_seed["name"])
        if requirement is None:
            requirement = KpEventServiceRequirement(
                service_id=service.id,
                **requirement_seed,
            )
        else:
            for key, value in requirement_seed.items():
                setattr(requirement, key, value)
        session.add(requirement)
        requirements_by_name[requirement.name] = requirement

    await session.flush()
    return service, requirements_by_name


async def get_or_create_zone_service_link(
    session,
    zone: KpEventBoothZone,
    service: KpEventService,
    included_quantity: int,
) -> KpEventBoothZoneServiceLink:
    link = (
        await session.execute(
            select(KpEventBoothZoneServiceLink).where(
                KpEventBoothZoneServiceLink.booth_zone_id == zone.id,
                KpEventBoothZoneServiceLink.service_id == service.id,
            )
        )
    ).scalar_one_or_none()

    if link is None:
        link = KpEventBoothZoneServiceLink(
            booth_zone_id=zone.id,
            service_id=service.id,
            included_quantity=included_quantity,
        )
    else:
        link.included_quantity = included_quantity

    session.add(link)
    await session.flush()
    return link


async def get_or_create_booking_service(
    session,
    booking: KpEventBooking,
    service: KpEventService,
    quantity: int,
    included_quantity: int,
) -> KpEventBookingService:
    booking_service = (
        await session.execute(
            select(KpEventBookingService).where(
                KpEventBookingService.booking_id == booking.id,
                KpEventBookingService.service_id == service.id,
            )
        )
    ).scalar_one_or_none()

    if booking_service is None:
        booking_service = KpEventBookingService(
            booking_id=booking.id,
            service_id=service.id,
            quantity=quantity,
            included_quantity=included_quantity,
        )
    else:
        booking_service.quantity = quantity
        booking_service.included_quantity = included_quantity

    session.add(booking_service)
    await session.flush()
    return booking_service


async def upsert_requirement_text_answer(
    session,
    booking_service: KpEventBookingService,
    requirement: KpEventServiceRequirement,
    text_value: str,
) -> KpEventBookingServiceFileLink:
    answer = (
        await session.execute(
            select(KpEventBookingServiceFileLink).where(
                KpEventBookingServiceFileLink.booking_service_id
                == booking_service.id,
                KpEventBookingServiceFileLink.requirement_id == requirement.id,
            )
        )
    ).scalar_one_or_none()

    if answer is None:
        answer = KpEventBookingServiceFileLink(
            booking_service_id=booking_service.id,
            requirement_id=requirement.id,
            text_value=text_value,
        )
    else:
        answer.stored_file_id = None
        answer.text_value = text_value

    session.add(answer)
    await session.flush()
    return answer


async def upload_seed_file(
    session,
    storage_service: StorageService,
    seed_file: DummyFileSeed,
) -> StoredFile:
    content = seed_file["content"] or make_background_png(width=480, height=270)
    stored_object = await storage_service.upload_bytes(
        key=seed_file["storage_key"],
        content=content,
        filename=seed_file["filename"],
        content_type=seed_file["content_type"],
    )

    stored_file = (
        await session.execute(
            select(StoredFile).where(StoredFile.storage_key == seed_file["storage_key"])
        )
    ).scalar_one_or_none()
    if stored_file is None:
        stored_file = StoredFile(
            storage_key=stored_object.key,
            original_filename=seed_file["filename"],
            mime_type=stored_object.mime_type,
            size_bytes=stored_object.size_bytes,
            sha256=stored_object.sha256,
            etag=stored_object.etag,
        )
    else:
        stored_file.original_filename = seed_file["filename"]
        stored_file.mime_type = stored_object.mime_type
        stored_file.size_bytes = stored_object.size_bytes
        stored_file.sha256 = stored_object.sha256
        stored_file.etag = stored_object.etag

    session.add(stored_file)
    await session.flush()
    return stored_file


async def upsert_requirement_file_answer(
    session,
    booking_service: KpEventBookingService,
    requirement: KpEventServiceRequirement,
    stored_file: StoredFile,
) -> KpEventBookingServiceFileLink:
    answer = (
        await session.execute(
            select(KpEventBookingServiceFileLink).where(
                KpEventBookingServiceFileLink.booking_service_id
                == booking_service.id,
                KpEventBookingServiceFileLink.requirement_id == requirement.id,
            )
        )
    ).scalar_one_or_none()

    if answer is None:
        answer = KpEventBookingServiceFileLink(
            booking_service_id=booking_service.id,
            requirement_id=requirement.id,
            stored_file_id=stored_file.id,
        )
    else:
        answer.stored_file_id = stored_file.id
        answer.text_value = None

    session.add(answer)
    await session.flush()
    return answer


async def get_or_create_industry(session, name: str) -> KpIndustry:
    industry = (
        await session.execute(select(KpIndustry).where(KpIndustry.name == name))
    ).scalar_one_or_none()
    if industry is None:
        industry = KpIndustry(name=name)
        session.add(industry)
        await session.flush()
    return industry


async def upsert_booking_company_details(
    session,
    booking: KpEventBooking,
    values: CompanyDetailsSeed,
) -> KpBookingCompanyDetails:
    details = (
        await session.execute(
            select(KpBookingCompanyDetails).where(
                KpBookingCompanyDetails.booking_id == booking.id
            )
        )
    ).scalar_one_or_none()

    detail_values = {key: value for key, value in values.items() if key != "industries"}
    if details is None:
        details = KpBookingCompanyDetails(booking_id=booking.id, **detail_values)
    else:
        for key, value in detail_values.items():
            setattr(details, key, value)
    session.add(details)
    await session.flush()

    await session.execute(
        delete(KpBookingCompanyDetailsIndustryLink).where(
            col(KpBookingCompanyDetailsIndustryLink.booking_company_details_id)
            == details.id
        )
    )
    for industry_name in values["industries"]:
        industry = await get_or_create_industry(session, industry_name)
        session.add(
            KpBookingCompanyDetailsIndustryLink(
                booking_company_details_id=details.id,
                industry_id=industry.id,
            )
        )

    await session.flush()
    return details


async def seed_kp_background(session, event: KpEvent) -> None:
    content = make_background_png()
    stored_object = await StorageService(get_settings()).upload_bytes(
        key=KP_BACKGROUND_STORAGE_KEY,
        content=content,
        filename="seed-nametag-background.png",
        content_type="image/png",
    )
    content_hash = hashlib.sha256(content).hexdigest()

    stored_file = (
        await session.execute(
            select(StoredFile).where(
                StoredFile.storage_key == KP_BACKGROUND_STORAGE_KEY
            )
        )
    ).scalar_one_or_none()
    if stored_file is None:
        stored_file = StoredFile(
            storage_key=KP_BACKGROUND_STORAGE_KEY,
            original_filename="seed-nametag-background.png",
            mime_type="image/png",
            size_bytes=len(content),
            sha256=content_hash,
            etag=stored_object.etag,
        )
    else:
        stored_file.original_filename = "seed-nametag-background.png"
        stored_file.mime_type = "image/png"
        stored_file.size_bytes = len(content)
        stored_file.sha256 = content_hash
        stored_file.etag = stored_object.etag
    session.add(stored_file)
    await session.flush()

    background = (
        await session.execute(
            select(KpEventNametagBackground).where(
                KpEventNametagBackground.event_id == event.id
            )
        )
    ).scalar_one_or_none()
    if background is None:
        background = KpEventNametagBackground(
            event_id=event.id,
            stored_file_id=stored_file.id,
        )
    else:
        background.stored_file_id = stored_file.id
    session.add(background)
    await session.flush()


async def seed_kp_nametag_exports(
    session,
    storage_service: StorageService,
) -> tuple[int, int, int, int, int, int, int, int]:
    event = await get_or_create_kp_event(session)
    zones = {
        name: await get_or_create_booth_zone(session, event, name, values)
        for name, values in KP_EXPORT_ZONES.items()
    }
    services: dict[str, KpEventService] = {}
    requirements: dict[str, dict[str, KpEventServiceRequirement]] = {}
    for service_name, service_values in KP_EXPORT_SERVICES.items():
        service, service_requirements = await get_or_create_service(
            session,
            event,
            service_name,
            service_values,
        )
        services[service_name] = service
        requirements[service_name] = service_requirements

        service_image = KP_SERVICE_IMAGE_FILES.get(service_name)
        if service_image is not None:
            stored_file = await upload_seed_file(session, storage_service, service_image)
            service.image_stored_file_id = stored_file.id
            session.add(service)
            await session.flush()

    for zone_name, included_services in KP_ZONE_INCLUDED_SERVICES.items():
        zone = zones[zone_name]
        for service_name, included_quantity in included_services.items():
            await get_or_create_zone_service_link(
                session,
                zone,
                services[service_name],
                included_quantity,
            )

    bookings: list[KpEventBooking] = []
    booked_service_count = 0
    requirement_answer_count = 0
    requirement_file_count = 0
    company_detail_count = 0
    for company_seed in KP_EXPORT_COMPANIES:
        company = await get_or_create_company(session, str(company_seed["name"]))
        zone = zones[str(company_seed["zone"])]
        booking = await get_or_create_booking(
            session,
            event,
            company,
            zone,
            int(company_seed["booth_nr"]),
        )
        bookings.append(booking)

        await session.execute(
            delete(NameTag).where(col(NameTag.booking_id) == booking.id)
        )
        for first_name, last_name, position in company_seed["nametags"]:
            session.add(
                NameTag(
                    booking_id=booking.id,
                    first_name=first_name,
                    last_name=last_name,
                    position=position,
                )
            )

        company_name = str(company_seed["name"])
        for service_name, booking_service_seed in KP_BOOKING_SERVICES.get(
            company_name, {}
        ).items():
            booking_service = await get_or_create_booking_service(
                session,
                booking,
                services[service_name],
                booking_service_seed["quantity"],
                booking_service_seed["included_quantity"],
            )
            booked_service_count += 1

            for requirement_name, text_value in booking_service_seed[
                "text_answers"
            ].items():
                requirement = requirements[service_name][requirement_name]
                await upsert_requirement_text_answer(
                    session,
                    booking_service,
                    requirement,
                    text_value,
                )
                requirement_answer_count += 1

            for requirement_name, file_seed in (
                KP_REQUIREMENT_FILE_ANSWERS.get(company_name, {})
                .get(service_name, {})
                .items()
            ):
                stored_file = await upload_seed_file(session, storage_service, file_seed)
                requirement = requirements[service_name][requirement_name]
                await upsert_requirement_file_answer(
                    session,
                    booking_service,
                    requirement,
                    stored_file,
                )
                requirement_file_count += 1

        details = KP_COMPANY_DETAILS.get(company_name)
        if details is not None:
            await upsert_booking_company_details(session, booking, details)
            company_detail_count += 1

    await seed_kp_background(session, event)
    nametag_count = sum(len(company["nametags"]) for company in KP_EXPORT_COMPANIES)
    return (
        len(KP_EXPORT_COMPANIES),
        len(bookings),
        nametag_count,
        len(KP_EXPORT_SERVICES),
        booked_service_count,
        requirement_answer_count,
        requirement_file_count,
        company_detail_count,
    )


async def seed() -> None:
    settings = get_settings()
    storage_service = StorageService(settings)
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        company_map: dict[str, Company] = {}

        for key, name in SEED_COMPANIES.items():
            company_map[key] = await get_or_create_company(session, name)

        generated_users = generate_seed_users()

        created = 0
        updated = 0

        for item in [*generated_users, *KNOWN_COMPANY_USERS]:
            existing = (
                await session.execute(select(User).where(User.email == item["email"]))
            ).scalar_one_or_none()

            company_key = item.get("company_key")
            company = company_map[company_key] if company_key else None

            if existing is None:
                user = User(
                    email=item["email"],
                    password=password_hash.hash(SEED_USER_PASSWORD),
                    first_name=item["first_name"],
                    last_name=item["last_name"],
                    is_admin=item["is_admin"],
                    is_staff=item["is_staff"],
                    is_company=item["is_company"],
                    user_confirmed=item["user_confirmed"],
                    email_confirmed=item["email_confirmed"],
                    company_id=company.id if company else None,
                )
                session.add(user)
                created += 1
            else:
                existing.first_name = item["first_name"]
                existing.last_name = item["last_name"]
                existing.is_admin = item["is_admin"]
                existing.is_staff = item["is_staff"]
                existing.is_company = item["is_company"]
                existing.user_confirmed = item["user_confirmed"]
                existing.email_confirmed = item["email_confirmed"]
                existing.company_id = company.id if company else None
                if not existing.password:
                    existing.password = password_hash.hash(SEED_USER_PASSWORD)
                session.add(existing)
                updated += 1

        (
            kp_companies,
            kp_bookings,
            kp_nametags,
            kp_services,
            kp_booked_services,
            kp_requirement_answers,
            kp_requirement_files,
            kp_company_details,
        ) = await seed_kp_nametag_exports(session, storage_service)

        await session.commit()

    await engine.dispose()
    print(
        "Seed complete. "
        f"created={created}, updated={updated}, "
        f"companies={len(SEED_COMPANIES)}, "
        f"users={sum(SEED_USER_COUNTS.values()) + len(KNOWN_COMPANY_USERS)}, "
        f'kp_event="{KP_EVENT_NAME}", kp_companies={kp_companies}, '
        f"kp_bookings={kp_bookings}, kp_nametags={kp_nametags}, "
        f"kp_services={kp_services}, kp_booked_services={kp_booked_services}, "
        f"kp_requirement_answers={kp_requirement_answers}, "
        f"kp_requirement_files={kp_requirement_files}, "
        f"kp_company_details={kp_company_details}"
    )


if __name__ == "__main__":
    asyncio.run(seed())
