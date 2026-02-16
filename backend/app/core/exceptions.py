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


class AppError(Exception):
    """Base class for all application-specific exceptions."""

    def __init__(
        self, message: str, code: str, identifier: str, status_code: int = 500
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.identifier = identifier
        self.status_code = status_code


class Unauthenticated(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "User is not authenticated", "error.unauthenticated", identifier, 401
        )


class UserNotFound(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "User not found in the database", "error.user_not_found", identifier, 404
        )


class KeycloakExchangeFailed(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "Keycloak exchange failed",
            "error.keycloak_exchange_failed",
            identifier,
            400,
        )


class TokenInvalid(AppError):
    def __init__(self, identifier: str):
        super().__init__("Token is invalid", "error.token_invalid", identifier, 400)


class NotAllowed(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "User is not allowed to make this request",
            "error.not_allowed",
            identifier,
            405,
        )


class EmailNotConfirmed(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "User email is not confirmed", "error.email_not_confirmed", identifier, 307
        )
        self.redirect_to = "/unconfirmed_email"


class UserNotConfirmed(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "User is not confirmed by an admin", "error.not_confirmed", identifier, 307
        )
        self.redirect_to = "/unconfirmed_user"
