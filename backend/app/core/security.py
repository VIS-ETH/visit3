from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from fastapi import Response
import jwt
from pwdlib import PasswordHash
from app.crud.user import (
    create_refresh_token_by_user,
    get_refresh_token,
    get_user_by_email,
    save_forget_password_token,
)
from app.config import get_settings
from app.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession

password_hash = PasswordHash.recommended()
ACCESS_TOKEN_EXPIRE = timedelta(minutes=15)
REFRESH_TOKEN_EXPIRE = timedelta(days=7)
FORGET_PASSWORD_TOKEN_EXPIRE = timedelta(minutes=10)


async def authenticate_user(session: AsyncSession, email: str, password: str):
    user = await get_user_by_email(session, email)
    if not user:
        return False
    if not verify_password(password, user.password):
        return False
    return user   

def create_access_token(user: User):
    to_encode = {"sub": user.email, "roles": user.roles_list}
    expire = datetime.now(timezone.utc) + ACCESS_TOKEN_EXPIRE
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, get_settings().SECRET_KEY, algorithm="HS256")
    return encoded_jwt


async def create_refresh_token(session: AsyncSession, user: User):
    raw_token = secrets.token_urlsafe(64)
    hashed_token = hashlib.sha256(raw_token.encode()).hexdigest()
    token = await create_refresh_token_by_user(
        session, user, hashed_token, datetime.now(timezone.utc) + REFRESH_TOKEN_EXPIRE
    )

    if not token:
        raise Exception

    return raw_token


async def verify_refresh_token(session: AsyncSession, raw_token: str):
    hashed_token = hashlib.sha256(raw_token.encode()).hexdigest()
    token = await get_refresh_token(session, hashed_token)
    if not token:
        return None
    else:
        return token


def verify_password(plain_password: str, hashed_password: str):
    return password_hash.verify(plain_password, hashed_password)


def hash_password(password: str):
    return password_hash.hash(password)


def set_refresh_cookie(response: Response, raw_refresh_token: str):
    response.set_cookie(
        key="refresh_token",
        value=raw_refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=int(REFRESH_TOKEN_EXPIRE.total_seconds()),
    )
    
async def create_forget_password_token(session: AsyncSession, email: str):
    token = secrets.token_urlsafe(32)
    user = await get_user_by_email(session, email)
    
    if not user:
        return None
    
    expire = datetime.now(timezone.utc) + FORGET_PASSWORD_TOKEN_EXPIRE
    
    await save_forget_password_token(session, token, user, expire)

    return token
