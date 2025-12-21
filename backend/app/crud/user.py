from sqlmodel import select
from app.deps import DbSessionDep
from app.models.user import User

def get_users(session: DbSessionDep):
    statement = select(User)
    user = session.exec(statement).all()
    return user

def get_user_by_username(session: DbSessionDep, username: str):
    statement = select(User).where(User.username == username)
    user = session.exec(statement).first()
    
    return user

def create_user(session: DbSessionDep, user: User):
    try:
        session.add(user)
        session.commit()
        
        session.refresh(user)
        return user 
    except Exception as e:
        session.rollback()
        raise e