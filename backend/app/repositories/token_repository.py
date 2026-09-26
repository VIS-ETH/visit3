import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, TypeVar
from uuid import UUID, uuid4

from sqlalchemy import update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement
from sqlmodel import col, or_, select

from app.core.utils import hash_str
from app.models.auth_tokens import LoginLinkToken
from app.models.user import ConfirmEmailToken, RefreshToken, ResetPasswordToken
from app.repositories.base import BaseRepository

TokenModelT = TypeVar(
    "TokenModelT", RefreshToken, ResetPasswordToken, ConfirmEmailToken, LoginLinkToken
)

REFRESH_TOKEN_EXPIRE = timedelta(days=7)
REFRESH_TOKEN_REUSE_GRACE = timedelta(seconds=10)
RESET_PASSWORD_TOKEN_EXPIRE = timedelta(minutes=10)
CONFIRM_EMAIL_TOKEN_EXPIRE = timedelta(days=3)
LOGIN_LINK_TOKEN_EXPIRE = timedelta(minutes=15)
LOGIN_LINK_MAX_USES = 3


@dataclass(frozen=True)
class LoginLinkUse:
    user_id: UUID
    target_path: str


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
        **values: Any,
    ):
        try:
            conditions: list[ColumnElement[bool]] = []
            if user_id is not None:
                conditions.append(col(model.user_id) == user_id)
            if hashed_token is not None:
                conditions.append(col(model.token) == hashed_token)
            if model is RefreshToken:
                values.setdefault("rotated_at", None)

            await self.update_where(model, *conditions, is_revoked=True, **values)
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise e

    async def create_refresh_token(
        self,
        user_id: UUID,
        family_id: UUID | None = None,
        idp_refresh_token: str | None = None,
    ) -> str:
        raw_token = self._create_token_value(64)
        try:
            token = RefreshToken(
                user_id=user_id,
                token=hash_str(raw_token),
                expires_at=datetime.now(timezone.utc) + REFRESH_TOKEN_EXPIRE,
                family_id=family_id or uuid4(),
                idp_refresh_token=idp_refresh_token,
            )
            self.session.add(token)
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise e
        return raw_token

    async def find_refresh_token(self, token: str) -> RefreshToken | None:
        statement = select(RefreshToken).where(RefreshToken.token == hash_str(token))
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def revoke_refresh_family(self, family_id: UUID) -> None:
        try:
            await self.update_where(
                RefreshToken,
                col(RefreshToken.family_id) == family_id,
                is_revoked=True,
                rotated_at=None,
            )
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise e

    async def get_active_refresh_token(self, token: str) -> RefreshToken | None:
        return await self._get_active_token(
            RefreshToken,
            hashed_token=hash_str(token),
        )

    async def get_refresh_token_for_rotation(self, token: str) -> RefreshToken | None:
        now = datetime.now(timezone.utc)
        statement = select(RefreshToken).where(
            RefreshToken.token == hash_str(token),
            RefreshToken.expires_at > now,
            or_(
                col(RefreshToken.is_revoked) == False,
                col(RefreshToken.rotated_at) > now - REFRESH_TOKEN_REUSE_GRACE,
            ),
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def revoke_refresh_token(self, user_id: UUID, token: str):
        await self._revoke_tokens(
            RefreshToken, user_id=user_id, hashed_token=hash_str(token)
        )

    async def rotate_refresh_token(self, user_id: UUID, token: str):
        await self._revoke_tokens(
            RefreshToken,
            user_id=user_id,
            hashed_token=hash_str(token),
            rotated_at=datetime.now(timezone.utc),
        )

    async def revoke_all_refresh_tokens(self, user_id: UUID):
        await self._revoke_tokens(RefreshToken, user_id=user_id)

    async def create_reset_password_token(self, user_id: UUID) -> str:
        return await self._issue_token(
            ResetPasswordToken,
            user_id=user_id,
            expires_at=datetime.now(timezone.utc) + RESET_PASSWORD_TOKEN_EXPIRE,
            length=32,
        )

    async def get_reset_password_token(self, token: str) -> ResetPasswordToken | None:
        return await self._get_active_token(
            ResetPasswordToken,
            hashed_token=hash_str(token),
        )

    async def revoke_reset_password_tokens(self, user_id: UUID):
        await self._revoke_tokens(ResetPasswordToken, user_id=user_id)

    async def create_confirm_email_token(self, user_id: UUID) -> str:
        return await self._issue_token(
            ConfirmEmailToken,
            user_id=user_id,
            expires_at=datetime.now(timezone.utc) + CONFIRM_EMAIL_TOKEN_EXPIRE,
            length=32,
        )

    async def get_confirm_email_token(self, token: str) -> ConfirmEmailToken | None:
        return await self._get_active_token(
            ConfirmEmailToken,
            hashed_token=hash_str(token),
        )

    async def revoke_confirm_email_tokens(self, user_id: UUID):
        await self._revoke_tokens(ConfirmEmailToken, user_id=user_id)

    async def create_login_link_token(self, user_id: UUID, target_path: str) -> str:
        token = self._create_token_value(48)
        try:
            link_token = LoginLinkToken(
                user_id=user_id,
                token=hash_str(token),
                expires_at=datetime.now(timezone.utc) + LOGIN_LINK_TOKEN_EXPIRE,
                target_path=target_path,
            )
            self.session.add(link_token)
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise e
        return token

    async def use_login_link_token(self, token: str) -> LoginLinkUse | None:
        now = datetime.now(timezone.utc)
        statement = (
            sql_update(LoginLinkToken)
            .where(
                col(LoginLinkToken.token) == hash_str(token),
                col(LoginLinkToken.expires_at) > now,
                col(LoginLinkToken.is_revoked) == False,
                col(LoginLinkToken.use_count) < LOGIN_LINK_MAX_USES,
            )
            .values(use_count=col(LoginLinkToken.use_count) + 1, used_at=now)
            .returning(col(LoginLinkToken.user_id), col(LoginLinkToken.target_path))
        )
        try:
            row = (await self.session.execute(statement)).first()
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise e
        if row is None:
            return None
        return LoginLinkUse(user_id=row[0], target_path=row[1])

    async def revoke_login_link_tokens(self, user_id: UUID):
        await self._revoke_tokens(LoginLinkToken, user_id=user_id)

    def _disposable(
        self, model: type[TokenModelT], now: datetime
    ) -> ColumnElement[bool]:
        expired = col(model.expires_at) < now
        if model is RefreshToken:
            return expired | (
                (col(RefreshToken.is_revoked) == True)
                & col(RefreshToken.rotated_at).is_(None)
            )
        return expired | (col(model.is_revoked) == True)

    async def cleanup_expired(self):
        try:
            now = datetime.now(timezone.utc)
            for model in (
                RefreshToken,
                ResetPasswordToken,
                ConfirmEmailToken,
                LoginLinkToken,
            ):
                await self.hard_delete_where(model, self._disposable(model, now))
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise e
