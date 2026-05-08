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
    KpBookingStatus,
    KpEvent,
    KpEventBooking,
    KpEventBoothZone,
    KpEventNametagBackground,
    NameTag,
)
from app.models.storage import StoredFile
from app.models.user import User
from app.services.storage_service import StorageService

password_hash = PasswordHash.recommended()


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
}

KP_EVENT_NAME = "Kontaktparty Nametag Export Test"
KP_BACKGROUND_STORAGE_KEY = "seed/nametag-export-test/background.png"

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


async def seed_kp_nametag_exports(session) -> tuple[int, int, int]:
    event = await get_or_create_kp_event(session)
    zones = {
        name: await get_or_create_booth_zone(session, event, name, values)
        for name, values in KP_EXPORT_ZONES.items()
    }

    bookings: list[KpEventBooking] = []
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

    await seed_kp_background(session, event)
    nametag_count = sum(len(company["nametags"]) for company in KP_EXPORT_COMPANIES)
    return len(KP_EXPORT_COMPANIES), len(bookings), nametag_count


async def seed() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        company_map: dict[str, Company] = {}

        for key, name in SEED_COMPANIES.items():
            company_map[key] = await get_or_create_company(session, name)

        generated_users = generate_seed_users()

        created = 0
        updated = 0

        for item in generated_users:
            existing = (
                await session.execute(select(User).where(User.email == item["email"]))
            ).scalar_one_or_none()

            company_key = item.get("company_key")
            company = company_map[company_key] if company_key else None

            if existing is None:
                user = User(
                    email=item["email"],
                    password=password_hash.hash("TestPassword123!"),
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
                    existing.password = password_hash.hash("TestPassword123!")
                session.add(existing)
                updated += 1

        kp_companies, kp_bookings, kp_nametags = await seed_kp_nametag_exports(session)

        await session.commit()

    await engine.dispose()
    print(
        "Seed complete. "
        f"created={created}, updated={updated}, "
        f"companies={len(SEED_COMPANIES)}, users={sum(SEED_USER_COUNTS.values())}, "
        f'kp_event="{KP_EVENT_NAME}", kp_companies={kp_companies}, '
        f"kp_bookings={kp_bookings}, kp_nametags={kp_nametags}"
    )


if __name__ == "__main__":
    asyncio.run(seed())
