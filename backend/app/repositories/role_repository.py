from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from app.models.user import Role
from app.repositories.base import BaseRepository


class RoleRepository(BaseRepository[Role]):
    def __init__(self, session: AsyncSession):
        super().__init__(Role, session)

    async def get_or_create(self, name: str):
        role = await self._get_by_field(col(Role.name), name)
        if role is not None:
            return role
        return await self.create_role(name)

    async def create_role(self, name: str):
        async with self.committing():
            role = Role(name=name)
            self.session.add(role)
        await self.session.refresh(role)
        return role
