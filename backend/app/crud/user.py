from sqlmodel import select
from app.deps import DbSessionDep
from app.models.user import User

async def get_users(session: DbSessionDep):
    statement = select(User)
    result = await session.execute(statement)
    user = result.scalars().all()
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