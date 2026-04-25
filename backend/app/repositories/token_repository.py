from datetime import datetime, timezone
from typing import TypeVar
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import DateTime, delete, select, update

from app.models.user import ConfirmEmailToken, ForgetPasswordToken, RefreshToken

TokenModelT = TypeVar(
    "TokenModelT", RefreshToken, ForgetPasswordToken, ConfirmEmailToken
)


class TokenRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _create_token(
        self,
        model: type[TokenModelT],
        *,
        user_id: UUID,
        hashed_token: str,
        expires_at: DateTime,
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
                statement = statement.where(model.user_id == user_id)
            if hashed_token is not None:
                statement = statement.where(model.token == hashed_token)

            await self.session.execute(statement.values(is_revoked=True))
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise e

    async def create_refresh_token(
        self, user_id: UUID, hashed_token: str, expires_at: DateTime
    ) -> RefreshToken:
        return await self._create_token(
            RefreshToken,
            user_id=user_id,
            hashed_token=hashed_token,
            expires_at=expires_at,
        )

    async def get_active_refresh_token(self, hashed_token: str) -> RefreshToken | None:
        return await self._get_active_token(
            RefreshToken,
            hashed_token=hashed_token,
        )

    async def revoke_refresh_token(self, user_id: UUID, hashed_token: str):
        await self._revoke_tokens(
            RefreshToken, user_id=user_id, hashed_token=hashed_token
        )

    async def revoke_all_refresh_tokens(self, user_id: UUID):
        await self._revoke_tokens(RefreshToken, user_id=user_id)

    async def save_forget_password_token(
        self, hashed_token: str, user_id: UUID, expires_at: DateTime
    ) -> ForgetPasswordToken:
        return await self._create_token(
            ForgetPasswordToken,
            user_id=user_id,
            hashed_token=hashed_token,
            expires_at=expires_at,
        )

    async def get_forget_password_token(
        self, hashed_token: str
    ) -> ForgetPasswordToken | None:
        return await self._get_active_token(
            ForgetPasswordToken,
            hashed_token=hashed_token,
        )

    async def revoke_forget_password_token(self, hashed_token: str):
        await self._revoke_tokens(ForgetPasswordToken, hashed_token=hashed_token)

    async def save_confirm_email_token(
        self, hashed_token: str, user_id: UUID, expires_at: DateTime
    ) -> ConfirmEmailToken:
        return await self._create_token(
            ConfirmEmailToken,
            user_id=user_id,
            hashed_token=hashed_token,
            expires_at=expires_at,
        )

    async def validate_confirm_email_token(
        self, user_id: UUID, hashed_token: str
    ) -> bool:
        return (
            await self._get_active_token(
                ConfirmEmailToken,
                user_id=user_id,
                hashed_token=hashed_token,
            )
            is not None
        )

    async def revoke_confirm_email_tokens(self, user_id: UUID):
        await self._revoke_tokens(ConfirmEmailToken, user_id=user_id)

    async def cleanup_expired(self):
        try:
            now = datetime.now(timezone.utc)
            for model in (RefreshToken, ForgetPasswordToken, ConfirmEmailToken):
                await self.session.execute(
                    delete(model).where(
                        (model.expires_at < now) | (model.is_revoked == True)
                    )
                )
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise e
