from datetime import datetime, timezone
import uuid
from sqlmodel import DateTime, update, select
from app.models.user import ForgetPasswordToken, RefreshToken, User
from sqlalchemy.ext.asyncio import AsyncSession


async def get_users(session: AsyncSession):
    statement = select(User)
    result = await session.execute(statement)
    user = result.scalars().all()
    return user


async def get_user_by_id(session: AsyncSession, user_id: uuid.UUID):
    statement = select(User).where(User.id == user_id)
    result = await session.execute(statement)
    user = result.scalar_one_or_none()
    return user


async def get_user_by_email(session: AsyncSession, email: str):
    statement = select(User).where(User.email == email)
    result = await session.execute(statement)
    user = result.scalar_one_or_none()
    return user


async def create_user(session: AsyncSession, user: User):
    try:
        session.add(user)
        await session.commit()

        await session.refresh(user)
        return user
    except Exception as e:
        await session.rollback()
        raise e


async def create_refresh_token_by_user(
    session: AsyncSession, user: User, token_str: str, expires_at: DateTime
):
    try:
        token = RefreshToken(user_id=user.id, token=token_str, expires_at=expires_at)

        session.add(token)
        await session.commit()

        await session.refresh(token)
        return token
    except Exception as e:
        await session.rollback()
        raise e


async def get_refresh_token(session: AsyncSession, raw_token: str):
    statement = select(RefreshToken).where(RefreshToken.token == raw_token)
    result = await session.execute(statement)
    token = result.scalar_one_or_none()
    return token


async def revoke_refresh_tokens(session: AsyncSession, user: User):
    try:
        statement = (
            update(RefreshToken)
            .where(RefreshToken.user_id == user.id)
            .values(is_revoked=True)
        )

        await session.execute(statement)
        await session.commit()
    except Exception as e:
        await session.rollback()
        raise e


async def save_forget_password_token(
    session: AsyncSession, token_str: str, user: User, expires_at: DateTime
):
    try:
        token = ForgetPasswordToken(
            user_id=user.id, token=token_str, expires_at=expires_at
        )

        session.add(token)
        await session.commit()

        await session.refresh(token)
        return token
    except Exception as e:
        await session.rollback()
        raise e


async def check_forget_password_token(session: AsyncSession, token_str: str):
    statement = select(ForgetPasswordToken).where(
        ForgetPasswordToken.token == token_str,
        ForgetPasswordToken.expires_at > datetime.now(timezone.utc),
        ForgetPasswordToken.is_revoked == False,
    )
    result = await session.execute(statement)
    return result.scalar_one_or_none() is not None


async def change_password(
    session: AsyncSession, token_str: str, new_password_hash: str
):
    try:
        statement = select(ForgetPasswordToken).where(
            ForgetPasswordToken.token == token_str,
            ForgetPasswordToken.expires_at > datetime.now(timezone.utc),
            ForgetPasswordToken.is_revoked == False,
        )

        result = await session.execute(statement)
        token = result.scalar_one()

        token.is_revoked = True
        session.add(token)

        statement = (
            update(User)
            .where(User.id == token.user_id)
            .values(password=new_password_hash),
            update(RefreshToken)
            .where(RefreshToken.user_id == token.user_id)
            .values(is_revoked=True)
        )

        await session.execute(statement)

        await session.commit()
        return True
    except Exception as e:
        await session.rollback()
        raise e
