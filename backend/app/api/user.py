from datetime import timedelta
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from app.deps import CurrentUserDep, DbSessionDep
from app.schemas.user import Token, UserCreate
from app.models.user import User
from app.crud.user import create_user, get_users
from app.core.security import ACCESS_TOKEN_EXPIRE_MINUTES, authenticate_user, create_access_token, hash_password

router = APIRouter(prefix="/users")

@router.get("/me")
def read_users_me(current_user: CurrentUserDep):
    if not current_user:
        raise HTTPException(
            status_code=401,
            detail="Unauthenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user

@router.post("/register")
async def register_user(session: DbSessionDep, user_create: UserCreate):
    user = User.model_validate(user_create)
    user.password = hash_password(user.password)
    
    try:
        return await create_user(session, user)
    except:
        raise HTTPException(status_code=400, detail="Creating user failed")
    
@router.get("/list")
async def list_users(session: DbSessionDep):
    return await get_users(session)

@router.post("/login")
async def login_user(session: DbSessionDep, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    user = await authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")

    
    

