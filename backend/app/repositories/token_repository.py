import secrets
from datetime import datetime, timedelta, timezone
from typing import TypeVar
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select, update

from app.core.utils import hash_str
from app.models.user import ConfirmEmailToken, RefreshToken, ResetPasswordToken
from app.repositories.base import BaseRepository

TokenModelT = TypeVar(
    "TokenModelT", RefreshToken, ResetPasswordToken, ConfirmEmailToken
)

REFRESH_TOKEN_EXPIRE = timedelta(days=7)
RESET_PASSWORD_TOKEN_EXPIRE = timedelta(minutes=10)
CONFIRM_EMAIL_TOKEN_EXPIRE = timedelta(days=3)


class TokenRepository(BaseRepository[RefreshToken]):
    def __init__(self, session: AsyncSession):
        super().__init__(RefreshToken, session)

    def _create_token_value(self, length: int) -> str:
        return secrets.token_urlsafe(length)

    async def _create_token(
        self,
        model: type[TokenModelT],
        *,
        user_id: UUID,
        hashed_token: str,
        expires_at: datetime,
    ) -> TokenModelT:
        try:
            token = model(user_id=user_id, token=hashed_token, expires_at=expires_at)
            self.session.add(token)
            await self.session.commit()
            await self.session.refresh(token)
            return token
        except Exception as e:
            await self.session.rollback()
            raise e

    async def _issue_token(
        self,
        model: type[TokenModelT],
        *,
        user_id: UUID,
        expires_at: datetime,
        length: int,
    ) -> str:
        token = self._create_token_value(length)
        await self._create_token(
            model,
            user_id=user_id,
            hashed_token=hash_str(token),
            expires_at=expires_at,
        )
        return token

    async def _get_active_token(
        self,
        model: type[TokenModelT],
        *,
        hashed_token: str,
        user_id: UUID | None = None,
    ) -> TokenModelT | None:
        conditions = [
            model.token == hashed_token,
            model.expires_at > datetime.now(timezone.utc),
            model.is_revoked == False,
        ]
        if user_id is not None:
            conditions.append(model.user_id == user_id)

        statement = select(model).where(*conditions)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def _revoke_tokens(
        self,
        model: type[TokenModelT],
        *,
        user_id: UUID | None = None,
        hashed_token: str | None = None,
    ):
        try:
            statement = update(model)
            if user_id is not None:
                statement = statement.where(col(model.user_id) == user_id)
            if hashed_token is not None:
                statement = statement.where(col(model.token) == hashed_token)

            await self.session.execute(statement.values(is_revoked=True))
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise e

    async def create_refresh_token(
        self, user_id: UUID
    ) -> str:
        return await self._issue_token(
            RefreshToken,
            user_id=user_id,
            expires_at=datetime.now(timezone.utc) + REFRESH_TOKEN_EXPIRE,
            length=64,
        )

    async def get_active_refresh_token(self, token: str) -> RefreshToken | None:
        return await self._get_active_token(
            RefreshToken,
            hashed_token=hash_str(token),
        )

    async def revoke_refresh_token(self, user_id: UUID, token: str):
        await self._revoke_tokens(
            RefreshToken, user_id=user_id, hashed_token=hash_str(token)
        )

    async def revoke_all_refresh_tokens(self, user_id: UUID):
        await self._revoke_tokens(RefreshToken, user_id=user_id)

    async def create_reset_password_token(
        self, user_id: UUID
    ) -> str:
        return await self._issue_token(
            ResetPasswordToken,
            user_id=user_id,
            expires_at=datetime.now(timezone.utc) + RESET_PASSWORD_TOKEN_EXPIRE,
            length=32,
        )

    async def get_reset_password_token(
        self, token: str
    ) -> ResetPasswordToken | None:
        return await self._get_active_token(
            ResetPasswordToken,
            hashed_token=hash_str(token),
        )

    async def revoke_reset_password_token(self, token: str):
        await self._revoke_tokens(
            ResetPasswordToken, hashed_token=hash_str(token)
        )

    async def create_confirm_email_token(
        self, user_id: UUID
    ) -> str:
        return await self._issue_token(
            ConfirmEmailToken,
            user_id=user_id,
            expires_at=datetime.now(timezone.utc) + CONFIRM_EMAIL_TOKEN_EXPIRE,
            length=32,
        )

    async def get_confirm_email_token(
        self, token: str
    ) -> ConfirmEmailToken | None:
        return await self._get_active_token(
            ConfirmEmailToken,
            hashed_token=hash_str(token),
        )

    async def revoke_confirm_email_tokens(self, user_id: UUID):
        await self._revoke_tokens(ConfirmEmailToken, user_id=user_id)

    async def cleanup_expired(self):
        try:
            now = datetime.now(timezone.utc)
            for model in (RefreshToken, ResetPasswordToken, ConfirmEmailToken):
                await self.hard_delete_where(
                    model,
                    (col(model.expires_at) < now) | (col(model.is_revoked) == True),
                )
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise e
