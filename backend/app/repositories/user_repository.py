from datetime import datetime, timezone
from typing import List
import uuid
from sqlmodel import DateTime, update, select
from app.core.exceptions import TokenInvalid
from app.core.utils import normalize_email
from app.models.user import ConfirmEmailToken, ForgetPasswordToken, RefreshToken, User
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_users(self):
        statement = select(User)
        result = await self.session.execute(statement)
        user = result.scalars().all()
        return user

    async def get_by_id(self, user_id: uuid.UUID):
        return await self._get_by_field(User.id, user_id)

    async def get_by_email(self, email: str):
        return await self._get_by_field(User.email, normalize_email(email))

    async def get_by_sub(self, sub: str):
        return await self._get_by_field(User.sub, sub)

    async def create_user(self, user: User):
        try:
            self.session.add(user)
            await self.session.commit()

            await self.session.refresh(user)
            return user
        except Exception as e:
            await self.session.rollback()
            raise e

    async def create_or_update_user(self, user: User):
        try:
            db_user = await self.get_by_email(user.email)
            if db_user is None:
                return await self.create_user(user)
            else:
                update_data = user.dict(exclude={"id"})
                for key, value in update_data.items():
                    setattr(db_user, key, value)
                self.session.add(db_user)
                await self.session.commit()
                await self.session.refresh(db_user)
                return db_user
        except Exception as e:
            await self.session.rollback()
            raise e

    async def get_roles_list(self, user: User):
        roles = []
        if user.is_admin:
            roles.append("admin")
        if user.is_staff:
            roles.append("staff")
        if user.is_company:
            roles.append("company")

        await self.session.refresh(user, attribute_names=["roles"])

        try:
            db_role_names = [r.name for r in user.roles]
            roles.extend(db_role_names)
        except Exception:
            pass

        return list(set(roles))

    async def create_refresh_token_by_user(
        self, user: User, token: str, expires_at: DateTime
    ):
        try:
            token = RefreshToken(user_id=user.id, token=token, expires_at=expires_at)

            self.session.add(token)
            await self.session.commit()

            await self.session.refresh(token)
            return token
        except Exception as e:
            await self.session.rollback()
            raise e

    async def get_refresh_token(self, hashed_token: str):
        statement = select(RefreshToken).where(RefreshToken.token == hashed_token)
        result = await self.session.execute(statement)
        token = result.scalar_one_or_none()
        return token

    async def revoke_refresh_tokens(self, user: User):
        try:
            statement = (
                update(RefreshToken)
                .where(RefreshToken.user_id == user.id)
                .values(is_revoked=True)
            )

            await self.session.execute(statement)
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise e

    async def revoke_refresh_token(self, user: User, hashed_token: str):
        try:
            statement = (
                update(RefreshToken)
                .where(
                    RefreshToken.token == hashed_token, RefreshToken.user_id == user.id
                )
                .values(is_revoked=True)
            )
            await self.session.execute(statement)
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise e

    async def save_forget_password_token(
        self, hashed_token: str, user: User, expires_at: DateTime
    ):
        try:
            token = ForgetPasswordToken(
                user_id=user.id, token=hashed_token, expires_at=expires_at
            )

            self.session.add(token)
            await self.session.commit()

            await self.session.refresh(token)
            return token
        except Exception as e:
            await self.session.rollback()
            raise e

    async def check_forget_password_token(self, hashed_token: str):
        statement = select(ForgetPasswordToken).where(
            ForgetPasswordToken.token == hashed_token,
            ForgetPasswordToken.expires_at > datetime.now(timezone.utc),
            ForgetPasswordToken.is_revoked == False,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none() is not None

    async def change_password(self, token_str: str, new_password_hash: str):
        try:
            statement = select(ForgetPasswordToken).where(
                ForgetPasswordToken.token == token_str,
                ForgetPasswordToken.expires_at > datetime.now(timezone.utc),
                ForgetPasswordToken.is_revoked == False,
            )

            result = await self.session.execute(statement)
            token = result.scalar_one_or_none()

            if not token:
                raise TokenInvalid("")

            user_update = (
                update(User)
                .where(User.id == token.user_id)
                .values(password=new_password_hash)
            )

            refresh_token_update = (
                update(RefreshToken)
                .where(RefreshToken.user_id == token.user_id)
                .values(is_revoked=True)
            )

            await self.session.execute(user_update)
            await self.session.execute(refresh_token_update)

            await self.session.commit()
            return True

        except Exception as e:
            await self.session.rollback()
            raise e

    async def confirm_email(self, user: User):
        try:
            user.email_confirmed = True
            self.session.add(user)
            self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise e

    async def revoke_confirm_email_tokens(self, user: User):
        try:
            statement = (
                update(ConfirmEmailToken)
                .where(ConfirmEmailToken.user_id == user.id)
                .values(is_revoked=True)
            )

            await self.session.execute(statement)
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise e

    async def validate_confirm_email_token(self, user: User, hashed_token: str):
        try:
            statement = select(ConfirmEmailToken).where(
                ConfirmEmailToken.user_id == user.id,
                ConfirmEmailToken.token == hashed_token,
                ConfirmEmailToken.is_revoked == False,
                ConfirmEmailToken.expires_at > datetime.now(timezone.utc),
            )
            result = await self.session.execute(statement)
            return result.scalar_one_or_none() is not None
        except Exception as e:
            await self.session.rollback()
            raise e

    async def save_confirm_email_token(
        self, hashed_token: str, user: User, expires_at: DateTime
    ):
        try:
            token = ConfirmEmailToken(
                token=hashed_token, user_id=user.id, expires_at=expires_at
            )
            self.session.add(token)
            await self.session.commit()
            await self.session.refresh(token)
            return token
        except Exception as e:
            await self.session.rollback()
            raise e
