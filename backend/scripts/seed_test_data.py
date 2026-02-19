from __future__ import annotations

import asyncio
import random
import sys
from pathlib import Path

from pwdlib import PasswordHash
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import select

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings
from app.models.company import Company
from app.models.user import User

password_hash = PasswordHash.recommended()

SEED_COMPANIES = {
    "seed-vendor": "Seed Vendor AG",
    "seed-partner": "Seed Partner GmbH",
}

RANDOM_SEED = 20260217

FIRST_NAMES = [
    "Ada", "Noah", "Mia", "Luca", "Nora", "Emil", "Lea", "Jonas", "Lina", "Felix",
    "Sofia", "David", "Emma", "Elias", "Mila", "Simon", "Jana", "Leo", "Nina", "Tim",
    "Sara", "Paul", "Clara", "Oskar", "Iris", "Roman", "Laura", "Ben", "Tina", "Kai",
]

LAST_NAMES = [
    "Meyer", "Schmidt", "Keller", "Fischer", "Wagner", "Weber", "Huber", "Koch", "Bauer", "Zimmermann",
    "Braun", "Hartmann", "Kruger", "Neumann", "Schulz", "Maier", "Becker", "Wolf", "Lang", "Klein",
    "Roth", "Krause", "Seidel", "Winter", "Peters", "Franke", "Jager", "Frei", "Graf", "Vogel",
]

EMAIL_POOL = [
    "atlas.user01@test.local", "atlas.user02@test.local", "atlas.user03@test.local", "atlas.user04@test.local",
    "atlas.user05@test.local", "atlas.user06@test.local", "atlas.user07@test.local", "atlas.user08@test.local",
    "atlas.user09@test.local", "atlas.user10@test.local", "nova.user11@test.local", "nova.user12@test.local",
    "nova.user13@test.local", "nova.user14@test.local", "nova.user15@test.local", "nova.user16@test.local",
    "nova.user17@test.local", "nova.user18@test.local", "nova.user19@test.local", "nova.user20@test.local",
    "terra.user21@test.local", "terra.user22@test.local", "terra.user23@test.local", "terra.user24@test.local",
    "terra.user25@test.local", "terra.user26@test.local", "terra.user27@test.local", "terra.user28@test.local",
    "terra.user29@test.local", "terra.user30@test.local", "orbit.user31@test.local", "orbit.user32@test.local",
    "orbit.user33@test.local", "orbit.user34@test.local", "orbit.user35@test.local", "orbit.user36@test.local",
    "orbit.user37@test.local", "orbit.user38@test.local", "orbit.user39@test.local", "orbit.user40@test.local",
    "pulse.user41@test.local", "pulse.user42@test.local", "pulse.user43@test.local", "pulse.user44@test.local",
    "pulse.user45@test.local", "pulse.user46@test.local", "pulse.user47@test.local", "pulse.user48@test.local",
]

SEED_USER_COUNTS = {
    "unconfirmed": 12,
    "staff": 12,
    "admins": 8,
    "company": 12,
}


def generate_seed_users() -> list[dict[str, object]]:
    randomizer = random.Random(RANDOM_SEED)
    shuffled_emails = EMAIL_POOL.copy()
    randomizer.shuffle(shuffled_emails)

    total_needed = sum(SEED_USER_COUNTS.values())
    if total_needed > len(shuffled_emails):
        raise ValueError(
            f"Not enough emails in EMAIL_POOL: need {total_needed}, have {len(shuffled_emails)}"
        )

    users: list[dict[str, object]] = []
    company_keys = list(SEED_COMPANIES.keys())
    email_index = 0

    for group, count in SEED_USER_COUNTS.items():
        for _ in range(count):
            email = shuffled_emails[email_index]
            email_index += 1

            first_name = randomizer.choice(FIRST_NAMES)
            last_name = randomizer.choice(LAST_NAMES)

            if group == "unconfirmed":
                user_payload = {
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
                    **user_payload,
                }
            )

            if user_payload["is_company"]:
                users[-1]["company_key"] = randomizer.choice(company_keys)

    return users


async def get_or_create_company(session, name: str) -> Company:
    company = (await session.execute(select(Company).where(Company.name == name))).scalar_one_or_none()
    if company:
        return company

    company = Company(name=name)
    session.add(company)
    await session.flush()
    return company


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

        await session.commit()

    await engine.dispose()
    print(
        "Seed complete. "
        f"created={created}, updated={updated}, "
        f"companies={len(SEED_COMPANIES)}, users={sum(SEED_USER_COUNTS.values())}"
    )


if __name__ == "__main__":
    asyncio.run(seed())
