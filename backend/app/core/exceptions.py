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


class CompanyNotFound(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "Company not found in the database",
            "error.company_not_found",
            identifier,
            404,
        )


class KpYearExists(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "KP event for this year already exists",
            "error.kp_year_exists",
            identifier,
            400,
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
            403,
        )


class EmailNotConfirmed(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "User email is not confirmed", "error.email_not_confirmed", identifier, 403
        )
        self.redirect_to = "/unconfirmed-email"


class UserNotConfirmed(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "User is not confirmed by an admin", "error.not_confirmed", identifier, 403
        )
        self.redirect_to = "/unconfirmed-user"


class PhoneNumberInvalid(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "Phone number is invalid", "error.phone_number_invalid", identifier, 400
        )


class PasswordWrong(AppError):
    def __init__(self, identifier: str):
        super().__init__("Password is wrong", "error.password_wrong", identifier, 400)


class EmailUsed(AppError):
    def __init__(self, identifier: str):
        super().__init__("Email is already used", "error.email_used", identifier, 400)


class PasswordTooShort(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "Password is too short", "error.password_too_short", identifier, 400
        )


class ResetPasswordError(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "Password reset failed", "error.reset_password_failed", identifier, 400
        )
