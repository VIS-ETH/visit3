from fastapi import HTTPException


unauth_e = HTTPException(
    status_code=401,
    detail="Unauthenticated",
    headers={"WWW-Authenticate": "Bearer"},
)

not_allowed_e = HTTPException(
    status_code=403,
    detail="Not allowed",
    headers={"WWW-Authenticate": "Bearer"},
)


class UserNotFoundError(Exception):
    def __init__(self, identifier: str):
        self.identifier = identifier


class KeycloakExchangeFailed(Exception):
    def __init__(self, identifier: str):
        self.identifier = identifier
