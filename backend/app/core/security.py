from datetime import datetime, timedelta, timezone
import jwt
from pwdlib import PasswordHash
from app.deps import DbSessionDep
from app.crud.user import get_user_by_username
from app.config import get_settings

password_hash = PasswordHash.recommended()
ACCESS_TOKEN_EXPIRE_MINUTES = 30

async def authenticate_user(session: DbSessionDep, username: str, password: str):
    user = await get_user_by_username(session, username)
    if not user:
        return False
    if not verify_password(password, user.password):
        return False
    return user

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, get_settings().SECRET_KEY, algorithm="HS256")
    return encoded_jwt

def verify_password(plain_password: str, hashed_password: str):
    return password_hash.verify(plain_password, hashed_password)
    
    
def hash_password(password:str):
    return password_hash.hash(password)