from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import DateTime, delete, select, update

from app.models.user import ConfirmEmailToken, ForgetPasswordToken, RefreshToken


class TokenRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_refresh_token(
        self, user_id: UUID, hashed_token: str, expires_at: DateTime
    ) -> RefreshToken:
        try:
            token = RefreshToken(user_id=user_id, token=hashed_token, expires_at=expires_at)
            self.session.add(token)
            await self.session.commit()
            await self.session.refresh(token)
            return token
        except Exception as e:
            await self.session.rollback()
            raise e

    async def get_refresh_token(self, hashed_token: str) -> RefreshToken | None:
        statement = select(RefreshToken).where(RefreshToken.token == hashed_token)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def revoke_refresh_token(self, user_id: UUID, hashed_token: str):
        try:
            await self.session.execute(
                update(RefreshToken)
                .where(RefreshToken.token == hashed_token, RefreshToken.user_id == user_id)
                .values(is_revoked=True)
            )
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise e

    async def revoke_all_refresh_tokens(self, user_id: UUID):
        try:
            await self.session.execute(
                update(RefreshToken)
                .where(RefreshToken.user_id == user_id)
                .values(is_revoked=True)
            )
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise e

    async def save_forget_password_token(
        self, hashed_token: str, user_id: UUID, expires_at: DateTime
    ) -> ForgetPasswordToken:
        try:
            token = ForgetPasswordToken(user_id=user_id, token=hashed_token, expires_at=expires_at)
            self.session.add(token)
            await self.session.commit()
            await self.session.refresh(token)
            return token
        except Exception as e:
            await self.session.rollback()
            raise e

    async def get_forget_password_token(self, hashed_token: str) -> ForgetPasswordToken | None:
        statement = select(ForgetPasswordToken).where(
            ForgetPasswordToken.token == hashed_token,
            ForgetPasswordToken.expires_at > datetime.now(timezone.utc),
            ForgetPasswordToken.is_revoked == False,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def revoke_forget_password_token(self, hashed_token: str):
        try:
            await self.session.execute(
                update(ForgetPasswordToken)
                .where(ForgetPasswordToken.token == hashed_token)
                .values(is_revoked=True)
            )
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise e

    async def save_confirm_email_token(
        self, hashed_token: str, user_id: UUID, expires_at: DateTime
    ) -> ConfirmEmailToken:
        try:
            token = ConfirmEmailToken(token=hashed_token, user_id=user_id, expires_at=expires_at)
            self.session.add(token)
            await self.session.commit()
            await self.session.refresh(token)
            return token
        except Exception as e:
            await self.session.rollback()
            raise e

    async def validate_confirm_email_token(self, user_id: UUID, hashed_token: str) -> bool:
        statement = select(ConfirmEmailToken).where(
            ConfirmEmailToken.user_id == user_id,
            ConfirmEmailToken.token == hashed_token,
            ConfirmEmailToken.is_revoked == False,
            ConfirmEmailToken.expires_at > datetime.now(timezone.utc),
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none() is not None

    async def revoke_confirm_email_tokens(self, user_id: UUID):
        try:
            await self.session.execute(
                update(ConfirmEmailToken)
                .where(ConfirmEmailToken.user_id == user_id)
                .values(is_revoked=True)
            )
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise e

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
