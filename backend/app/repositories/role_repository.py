from app.models.user import Role, User
from app.repositories.base import BaseRepository
from sqlalchemy.ext.asyncio import AsyncSession


class RoleRepository(BaseRepository[Role]):
    def __init__(self, session: AsyncSession):
        super().__init__(Role, session)

    async def get_or_create(self, name: str):
        role = await self._get_by_field(Role.name, name)
        if role is not None:
            return role
        return await self.create_role(name)

    async def create_role(self, name: str):
        role = Role(name=name)
        self.session.add(role)

        try:
            await self.session.commit()
            await self.session.refresh(role)
        except Exception as e:
            await self.session.rollback()
            raise e
        return role
