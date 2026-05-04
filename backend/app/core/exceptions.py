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


class CompanyUserNotFound(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "Selected user does not belong to the company",
            "error.company_user_not_found",
            identifier,
            400,
        )


class KpNameExists(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "KP event with this name already exists",
            "error.kp_name_exists",
            identifier,
            400,
        )


class KpBookingNotFound(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "KP booking not found",
            "error.kp_booking_not_found",
            identifier,
            404,
        )


class KpBookingNotOwned(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "KP booking does not belong to the current company",
            "error.kp_booking_not_owned",
            identifier,
            403,
        )


class KpBoothZoneNotFound(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "KP booth zone not found",
            "error.kp_booth_zone_not_found",
            identifier,
            404,
        )


class KpBoothZoneEventMismatch(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "KP booth zone belongs to a different event",
            "error.kp_booth_zone_event_mismatch",
            identifier,
            400,
        )


class KpWaitlistSameZone(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "Cannot add the current booth zone to the waitlist",
            "error.kp_waitlist_same_zone",
            identifier,
            400,
        )


class KpRegistrationClosed(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "Registration window for this KP event is not open",
            "error.kp_registration_closed",
            identifier,
            403,
        )


class KpBoothZoneAtCapacity(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "The selected booth zone has no remaining capacity",
            "error.kp_booth_zone_at_capacity",
            identifier,
            409,
        )


class KpBookingAlreadyExists(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "Your company already has an active booking for this event",
            "error.kp_booking_already_exists",
            identifier,
            409,
        )


class KpBookingStatusTransitionInvalid(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "The requested KP booking status transition is invalid",
            "error.kp_booking_status_transition_invalid",
            identifier,
            400,
        )


class KpBookingConfirmationRequiresFinalized(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "Only finalized KP bookings can be confirmed",
            "error.kp_booking_confirmation_requires_finalized",
            identifier,
            400,
        )


class KpEventNotFound(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "KP event not found",
            "error.kp_event_not_found",
            identifier,
            404,
        )


class KpServiceNotFound(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "KP service not found",
            "error.kp_service_not_found",
            identifier,
            404,
        )


class KpIndustryNotFound(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "KP industry not found",
            "error.kp_industry_not_found",
            identifier,
            404,
        )


class KpIndustryNameExists(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "KP industry with this name already exists",
            "error.kp_industry_name_exists",
            identifier,
            400,
        )


class KpServiceRequirementNotFound(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "KP service requirement not found",
            "error.kp_service_requirement_not_found",
            identifier,
            404,
        )


class KpRequirementBookingServiceMismatch(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "KP service requirement does not belong to a booked service",
            "error.kp_requirement_booking_service_mismatch",
            identifier,
            400,
        )


class StorageUploadFailed(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "File upload failed",
            "error.storage_upload_failed",
            identifier,
            500,
        )


class StorageDeleteFailed(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "File deletion failed",
            "error.storage_delete_failed",
            identifier,
            500,
        )


class StorageFileTooLarge(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "The uploaded file is too large",
            "error.storage_file_too_large",
            identifier,
            400,
        )


class StorageFileInvalidMimeType(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "The uploaded file type is not allowed",
            "error.storage_file_invalid_mime_type",
            identifier,
            400,
        )


class KpRequirementFileUploadNotAllowed(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "This requirement does not accept file uploads",
            "error.kp_requirement_file_upload_not_allowed",
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


class UserNotConfirmed(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "User is not confirmed by an admin", "error.not_confirmed", identifier, 403
        )


class PhoneNumberInvalid(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "Phone number is invalid", "error.phone_number_invalid", identifier, 400
        )


class InvalidCredentials(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "Invalid credentials", "error.invalid_credentials", identifier, 400
        )


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


class InviteNotFound(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "Invite not found or already used",
            "error.invite_not_found",
            identifier,
            404,
        )


class InviteExpired(AppError):
    def __init__(self, identifier: str):
        super().__init__("Invite has expired", "error.invite_expired", identifier, 400)
