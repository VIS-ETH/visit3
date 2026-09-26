from collections.abc import Sequence
from typing import Any


class AppError(Exception):
    def __init__(
        self,
        message: str,
        code: str,
        identifier: str,
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.identifier = identifier
        self.status_code = status_code
        self.details = details


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


class CompanyInvitePending(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "An unused invite for this email already exists",
            "error.company_invite_pending",
            identifier,
            409,
        )


class CompanyProfileIncomplete(AppError):
    def __init__(self, identifier: str, missing_fields: Sequence[str]):
        super().__init__(
            "Company profile is missing mandatory fields",
            "error.company_profile_incomplete",
            identifier,
            409,
            {"missingFields": list(missing_fields)},
        )


class CompanyProfileUnconfirmed(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "The company profile has to be confirmed before registering",
            "error.company_profile_unconfirmed",
            identifier,
            400,
        )


class IndustryNotFound(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "Industry not found",
            "error.industry_not_found",
            identifier,
            404,
        )


class IndustryNameExists(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "An industry with this name already exists",
            "error.industry_name_exists",
            identifier,
            409,
        )


class CompanyHasUpcomingBookings(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "Company still has bookings for upcoming KP events",
            "error.company_has_upcoming_bookings",
            identifier,
            409,
        )


class UserLastCompanyMember(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "Company would lose its last member while bookings are upcoming",
            "error.user_last_company_member",
            identifier,
            409,
        )


class UserAlreadyInCompany(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "User already belongs to a company",
            "error.user_already_in_company",
            identifier,
            409,
        )


class KpNameExists(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "KP event with this name already exists",
            "error.kp_name_exists",
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


class KpNameTagNotFound(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "KP name tag not found",
            "error.kp_name_tag_not_found",
            identifier,
            404,
        )


class KpExportBackgroundNotFound(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "KP export background not found",
            "error.kp_export_background_not_found",
            identifier,
            404,
        )


class KpExportEmpty(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "No name tags are available for this export",
            "error.kp_export_empty",
            identifier,
            400,
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


class KpBoothZoneNameExists(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "KP booth zone with this name already exists for this event",
            "error.kp_booth_zone_name_exists",
            identifier,
            409,
        )


class KpBoothZoneColorExists(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "KP booth zone with this color already exists for this event",
            "error.kp_booth_zone_color_exists",
            identifier,
            409,
        )


class KpBoothZoneInUse(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "KP booth zone is still used by an active booking",
            "error.kp_booth_zone_in_use",
            identifier,
            409,
        )


class KpWaitlistSameZone(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "Cannot add the current booth zone to the waitlist",
            "error.kp_waitlist_same_zone",
            identifier,
            400,
        )


class KpWaitlistZoneHasCapacity(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "The selected booth zone still has free capacity",
            "error.kp_waitlist_zone_has_capacity",
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


class KpBoothZoneFull(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "The selected booth zone is full",
            "error.kp_booth_zone_full",
            identifier,
            409,
        )


class KpBookingZoneLocked(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "Confirmed KP bookings can no longer change their booth zone",
            "error.kp_booking_zone_locked",
            identifier,
            409,
        )


class KpBookingZoneSwitchNotAllowed(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "This KP booking cannot switch to the requested booth zone",
            "error.kp_booking_zone_switch_not_allowed",
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


class KpBoothNumberTaken(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "Another active booking in this booth zone already uses this booth number",
            "error.kp_booth_number_taken",
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


class KpBookingDeleteRequiresForce(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "Confirmed KP bookings can only be deleted with force",
            "error.kp_booking_delete_requires_force",
            identifier,
            409,
        )


class KpBookingReadonly(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "Cancelled or rejected KP bookings can no longer be changed",
            "error.kp_booking_readonly",
            identifier,
            403,
        )


class KpFinalizationDeadlinePassed(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "The change deadline for this KP event has passed",
            "error.kp_finalization_deadline_passed",
            identifier,
            403,
        )


class KpServiceNotFound(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "KP service not found",
            "error.kp_service_not_found",
            identifier,
            404,
        )


class KpServiceNameExists(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "KP service with this name already exists for this event",
            "error.kp_service_name_exists",
            identifier,
            409,
        )


class KpServiceInUse(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "KP service is still booked by an active booking",
            "error.kp_service_in_use",
            identifier,
            409,
        )


class KpServiceUnavailable(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "KP service is unavailable",
            "error.kp_service_unavailable",
            identifier,
            400,
        )


class KpServiceQuantityInvalid(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "KP service quantity is invalid",
            "error.kp_service_quantity_invalid",
            identifier,
            400,
        )


class KpServiceEventMismatch(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "KP service belongs to a different KP event",
            "error.kp_service_event_mismatch",
            identifier,
            400,
        )


class KpIncludedServiceDuplicate(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "KP service is included more than once in this booth zone",
            "error.kp_included_service_duplicate",
            identifier,
            400,
        )


class KpIncludedExceedsMax(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "The included quantity exceeds the maximum quantity per booking",
            "error.kp_included_exceeds_max",
            identifier,
            400,
        )


class KpNametagLimitReached(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "This booking has reached its maximum number of name tags",
            "error.kp_nametag_limit_reached",
            identifier,
            400,
        )


class KpNametagsDeadlinePassed(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "The name tag deadline for this KP event has passed",
            "error.kp_nametags_deadline_passed",
            identifier,
            403,
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


class KpVenueLayoutNotFound(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "KP venue layout not found",
            "error.kp_venue_layout_not_found",
            identifier,
            404,
        )


class KpVenueLayoutNameExists(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "KP venue layout with this name already exists for this event",
            "error.kp_venue_layout_name_exists",
            identifier,
            409,
        )


class KpVenueOutOfBounds(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "The position lies outside the venue layout bounds",
            "error.kp_venue_out_of_bounds",
            identifier,
            400,
        )


class KpVenueBoothNumberDuplicate(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "The same booth number is placed more than once in this layout",
            "error.kp_venue_booth_number_duplicate",
            identifier,
            409,
        )


class MailUnavailable(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "The mail service is unavailable",
            "error.mail_unavailable",
            identifier,
            503,
        )


class CompanyNameTaken(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "Another company already uses this name",
            "error.company_name_taken",
            identifier,
            409,
        )


class ConcurrentChange(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "The data was changed at the same time elsewhere",
            "error.conflict",
            identifier,
            409,
        )


class StorageUploadFailed(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "File storage is unavailable",
            "error.storage_upload_failed",
            identifier,
            503,
        )


class StorageDeleteFailed(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "File deletion failed",
            "error.storage_delete_failed",
            identifier,
            500,
        )


class StorageDownloadFailed(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "File download failed",
            "error.storage_download_failed",
            identifier,
            500,
        )


class BookletBackgroundRejected(AppError):
    def __init__(
        self, reason: str, identifier: str, details: dict[str, object] | None = None
    ):
        super().__init__(
            "The booklet background was rejected",
            f"error.booklet_background_{reason}",
            identifier,
            400,
            details,
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


class KpRequirementTextAnswerNotAllowed(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "This requirement does not accept text answers",
            "error.kp_requirement_text_answer_not_allowed",
            identifier,
            400,
        )


class MailTemplateNotFound(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "Mail template not found",
            "error.mail_template_not_found",
            identifier,
            404,
        )


class MailTemplateInvalid(AppError):
    def __init__(
        self,
        identifier: str,
        detail: str,
        field: str,
        variable: str | None = None,
    ):
        details = {"field": field}
        if variable is not None:
            details["variable"] = variable
        super().__init__(
            f"Mail template is invalid: {detail}",
            "error.mail_template_invalid",
            identifier,
            400,
            details,
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


class EmailTakenLocally(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "Email already belongs to a local account",
            "auth.email_taken_locally",
            identifier,
            403,
        )


class NotVisMember(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "User has no active VIS membership role",
            "auth.not_vis_member",
            identifier,
            403,
        )


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


class InviteEmailMismatch(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "Invite was issued for a different email address",
            "error.invite_email_mismatch",
            identifier,
            403,
        )


class RateLimited(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "Too many requests, please try again later",
            "error.rate_limited",
            identifier,
            429,
        )


class CsrfInvalid(AppError):
    def __init__(self, identifier: str):
        super().__init__(
            "CSRF validation failed", "csrf.validation_failed", identifier, 403
        )
