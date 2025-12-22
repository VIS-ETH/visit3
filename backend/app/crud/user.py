import secrets
import uuid
from sqlmodel import DateTime, update, select
from app.deps import CurrentUserDep, DbSessionDep
from app.models.user import RefreshToken, User


async def get_users(session: DbSessionDep):
    statement = select(User)
    result = await session.execute(statement)
    user = result.scalars().all()
    return user


async def get_user_by_id(session: DbSessionDep, user_id: uuid.UUID):
    statement = select(User).where(User.id == user_id)
    result = await session.execute(statement)
    user = result.scalar_one_or_none()
    return user


async def get_user_by_email(session: DbSessionDep, email: str):
    statement = select(User).where(User.email == email)
    result = await session.execute(statement)
    user = result.scalar_one_or_none()
    return user


async def create_user(session: DbSessionDep, user: User):
    try:
        session.add(user)
        await session.commit()

        await session.refresh(user)
        return user
    except Exception as e:
        await session.rollback()
        raise e


async def create_refresh_token_by_user(
    session: DbSessionDep, user: User, token_str: str, expires_at: DateTime
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


async def get_refresh_token(session: DbSessionDep, raw_token: str):
    statement = select(RefreshToken).where(RefreshToken.token == raw_token)
    result = await session.execute(statement)
    token = result.scalar_one_or_none()
    return token


async def revoke_refresh_tokens(session: DbSessionDep, current_user: CurrentUserDep):
    try:
        statement = (
            update(RefreshToken)
            .where(RefreshToken.user_id == current_user.id)
            .values(is_revoked=True)
        )

        await session.execute(statement)
    except Exception as e:
        await session.rollback()
        raise e
