from fastapi import HTTPException


unauth_e = HTTPException(
    status_code=401,
    detail="Unauthenticated",
    headers={"WWW-Authenticate": "Bearer"},
)

not_allowed_e = HTTPException(
    status_code=401,
    detail="Unauthenticated",
    headers={"WWW-Authenticate": "Bearer"},
)