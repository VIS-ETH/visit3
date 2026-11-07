from collections.abc import Sequence
from typing import Any


class AppError(Exception):
    message: str
    code: str
    status_code: int = 500

    def __init__(self, identifier: str, details: dict[str, Any] | None = None):
        super().__init__(self.message)
        self.identifier = identifier
        self.details = details


class Unauthenticated(AppError):
    message = "User is not authenticated"
    code = "error.unauthenticated"
    status_code = 401


class UserNotFound(AppError):
    message = "User not found in the database"
    code = "error.user_not_found"
    status_code = 404


class CompanyNotFound(AppError):
    message = "Company not found in the database"
    code = "error.company_not_found"
    status_code = 404


class CompanyGeneralEmailIsLogin(AppError):
    message = "The general email must differ from the login emails of the company"
    code = "error.company_general_email_is_login"
    status_code = 400


class CompanyUserNotFound(AppError):
    message = "Selected user does not belong to the company"
    code = "error.company_user_not_found"
    status_code = 400


class CompanyInvitePending(AppError):
    message = "An unused invite for this email already exists"
    code = "error.company_invite_pending"
    status_code = 409


class CompanyProfileIncomplete(AppError):
    message = "Company profile is missing mandatory fields"
    code = "error.company_profile_incomplete"
    status_code = 409

    def __init__(self, identifier: str, missing_fields: Sequence[str]):
        super().__init__(identifier, {"missingFields": list(missing_fields)})


class CompanyProfileUnconfirmed(AppError):
    message = "The company profile has to be confirmed before registering"
    code = "error.company_profile_unconfirmed"
    status_code = 400


class IndustryNotFound(AppError):
    message = "Industry not found"
    code = "error.industry_not_found"
    status_code = 404


class IndustryNameExists(AppError):
    message = "An industry with this name already exists"
    code = "error.industry_name_exists"
    status_code = 409


class CompanyHasUpcomingBookings(AppError):
    message = "Company still has bookings for upcoming KP events"
    code = "error.company_has_upcoming_bookings"
    status_code = 409


class UserLastCompanyMember(AppError):
    message = "Company would lose its last member while bookings are upcoming"
    code = "error.user_last_company_member"
    status_code = 409


class UserAlreadyInCompany(AppError):
    message = "User already belongs to a company"
    code = "error.user_already_in_company"
    status_code = 409


class KpNameExists(AppError):
    message = "KP event with this name already exists"
    code = "error.kp_name_exists"
    status_code = 400


class KpEventNotFound(AppError):
    message = "KP event not found"
    code = "error.kp_event_not_found"
    status_code = 404


class KpBookingNotFound(AppError):
    message = "KP booking not found"
    code = "error.kp_booking_not_found"
    status_code = 404


class KpBookingNotOwned(AppError):
    message = "KP booking does not belong to the current company"
    code = "error.kp_booking_not_owned"
    status_code = 403


class KpNameTagNotFound(AppError):
    message = "KP name tag not found"
    code = "error.kp_name_tag_not_found"
    status_code = 404


class KpExportBackgroundNotFound(AppError):
    message = "KP export background not found"
    code = "error.kp_export_background_not_found"
    status_code = 404


class KpExportEmpty(AppError):
    message = "No name tags are available for this export"
    code = "error.kp_export_empty"
    status_code = 400


class KpBoothZoneNotFound(AppError):
    message = "KP booth zone not found"
    code = "error.kp_booth_zone_not_found"
    status_code = 404


class KpBoothZoneEventMismatch(AppError):
    message = "KP booth zone belongs to a different event"
    code = "error.kp_booth_zone_event_mismatch"
    status_code = 400


class KpBoothZoneNameExists(AppError):
    message = "KP booth zone with this name already exists for this event"
    code = "error.kp_booth_zone_name_exists"
    status_code = 409


class KpBoothZoneColorExists(AppError):
    message = "KP booth zone with this color already exists for this event"
    code = "error.kp_booth_zone_color_exists"
    status_code = 409


class KpBoothZoneOrderInvalid(AppError):
    message = "KP booth zone order must list every zone of the event exactly once"
    code = "error.kp_booth_zone_order_invalid"
    status_code = 400


class KpBoothZoneInUse(AppError):
    message = "KP booth zone is still used by an active booking"
    code = "error.kp_booth_zone_in_use"
    status_code = 409


class KpWaitlistSameZone(AppError):
    message = "Cannot add the current booth zone to the waitlist"
    code = "error.kp_waitlist_same_zone"
    status_code = 400


class KpWaitlistZoneHasCapacity(AppError):
    message = "The selected booth zone still has free capacity"
    code = "error.kp_waitlist_zone_has_capacity"
    status_code = 400


class KpRegistrationClosed(AppError):
    message = "Registration window for this KP event is not open"
    code = "error.kp_registration_closed"
    status_code = 403


class KpOfferExpired(AppError):
    message = "The deadline to confirm this offered place has passed"
    code = "error.kp_offer_expired"
    status_code = 409


class KpOfferPending(AppError):
    message = "This offered place has to be confirmed before it can be changed"
    code = "error.kp_offer_pending"
    status_code = 409


class KpTermsNotAccepted(AppError):
    message = "The terms and conditions have to be accepted"
    code = "error.kp_terms_not_accepted"
    status_code = 422


class KpBookingNotOffered(AppError):
    message = "This booking was not offered by VIS"
    code = "error.kp_booking_not_offered"
    status_code = 409


class KpOfferDeadlineInvalid(AppError):
    message = "The cancellation deadline must lie between today and the event"
    code = "error.kp_offer_deadline_invalid"
    status_code = 422


class KpZoneRegistrationClosed(AppError):
    message = "Registration for this booth zone is not open"
    code = "error.kp_zone_registration_closed"
    status_code = 403


class KpBoothZoneAtCapacity(AppError):
    message = "The selected booth zone has no remaining capacity"
    code = "error.kp_booth_zone_at_capacity"
    status_code = 409


class KpBoothZoneFull(AppError):
    message = "The selected booth zone is full"
    code = "error.kp_booth_zone_full"
    status_code = 409


class KpBookingZoneLocked(AppError):
    message = "Confirmed KP bookings can no longer change their booth zone"
    code = "error.kp_booking_zone_locked"
    status_code = 409


class KpBookingZoneSwitchNotAllowed(AppError):
    message = "This KP booking cannot switch to the requested booth zone"
    code = "error.kp_booking_zone_switch_not_allowed"
    status_code = 409


class KpBookingAlreadyExists(AppError):
    message = "Your company already has an active booking for this event"
    code = "error.kp_booking_already_exists"
    status_code = 409


class KpBoothNumberTaken(AppError):
    message = "Another active booking in this booth zone already uses this booth number"
    code = "error.kp_booth_number_taken"
    status_code = 409


class KpBookingStatusTransitionInvalid(AppError):
    message = "The requested KP booking status transition is invalid"
    code = "error.kp_booking_status_transition_invalid"
    status_code = 400


class KpBookingDeleteRequiresForce(AppError):
    message = "Confirmed KP bookings can only be deleted with force"
    code = "error.kp_booking_delete_requires_force"
    status_code = 409


class KpBookingReadonly(AppError):
    message = "Cancelled or rejected KP bookings can no longer be changed"
    code = "error.kp_booking_readonly"
    status_code = 403


class KpFinalizationDeadlinePassed(AppError):
    message = "The change deadline for this KP event has passed"
    code = "error.kp_finalization_deadline_passed"
    status_code = 403


class KpServiceNotFound(AppError):
    message = "KP service not found"
    code = "error.kp_service_not_found"
    status_code = 404


class KpServiceNameExists(AppError):
    message = "KP service with this name already exists for this event"
    code = "error.kp_service_name_exists"
    status_code = 409


class KpServiceInUse(AppError):
    message = "KP service is still booked by an active booking"
    code = "error.kp_service_in_use"
    status_code = 409


class KpServiceUnavailable(AppError):
    message = "KP service is unavailable"
    code = "error.kp_service_unavailable"
    status_code = 400


class KpServiceQuantityInvalid(AppError):
    message = "KP service quantity is invalid"
    code = "error.kp_service_quantity_invalid"
    status_code = 400


class KpServiceEventMismatch(AppError):
    message = "KP service belongs to a different KP event"
    code = "error.kp_service_event_mismatch"
    status_code = 400


class KpIncludedServiceDuplicate(AppError):
    message = "KP service is included more than once in this booth zone"
    code = "error.kp_included_service_duplicate"
    status_code = 400


class KpServiceRelationInvalid(AppError):
    message = "KP service cannot contain or exclude this service"
    code = "error.kp_service_relation_invalid"
    status_code = 400


class KpServicesExcluded(AppError):
    message = "These KP services cannot be booked together"
    code = "error.kp_services_excluded"
    status_code = 400


class KpIncludedExceedsMax(AppError):
    message = "The included quantity exceeds the maximum quantity per booking"
    code = "error.kp_included_exceeds_max"
    status_code = 400


class KpNametagLimitReached(AppError):
    message = "This booking has reached its maximum number of name tags"
    code = "error.kp_nametag_limit_reached"
    status_code = 400


class KpNametagsDeadlinePassed(AppError):
    message = "The name tag deadline for this KP event has passed"
    code = "error.kp_nametags_deadline_passed"
    status_code = 403


class KpServiceRequirementNotFound(AppError):
    message = "KP service requirement not found"
    code = "error.kp_service_requirement_not_found"
    status_code = 404


class KpRequirementBookingServiceMismatch(AppError):
    message = "KP service requirement does not belong to a booked service"
    code = "error.kp_requirement_booking_service_mismatch"
    status_code = 400


class KpVenueLayoutNotFound(AppError):
    message = "KP venue layout not found"
    code = "error.kp_venue_layout_not_found"
    status_code = 404


class KpVenueLayoutNameExists(AppError):
    message = "KP venue layout with this name already exists for this event"
    code = "error.kp_venue_layout_name_exists"
    status_code = 409


class KpVenueOutOfBounds(AppError):
    message = "The position lies outside the venue layout bounds"
    code = "error.kp_venue_out_of_bounds"
    status_code = 400


class KpVenueBoothNumberDuplicate(AppError):
    message = "The same booth number is placed more than once in this layout"
    code = "error.kp_venue_booth_number_duplicate"
    status_code = 409


class IdentityProviderUnavailable(AppError):
    message = "The identity provider is unavailable"
    code = "error.identity_provider_unavailable"
    status_code = 503


class MailUnavailable(AppError):
    message = "The mail service is unavailable"
    code = "error.mail_unavailable"
    status_code = 503


class CompanyNameTaken(AppError):
    message = "Another company already uses this name"
    code = "error.company_name_taken"
    status_code = 409


class ConcurrentChange(AppError):
    message = "The data was changed at the same time elsewhere"
    code = "error.conflict"
    status_code = 409


class StorageUploadFailed(AppError):
    message = "File storage is unavailable"
    code = "error.storage_upload_failed"
    status_code = 503


class StorageDeleteFailed(AppError):
    message = "File deletion failed"
    code = "error.storage_delete_failed"
    status_code = 500


class StorageDownloadFailed(AppError):
    message = "File download failed"
    code = "error.storage_download_failed"
    status_code = 500


class EventBannerTooSmall(AppError):
    message = "The banner image is too small"
    code = "error.event_banner_too_small"
    status_code = 400


class BookletBackgroundRejected(AppError):
    message = "The booklet background was rejected"
    status_code = 400

    def __init__(
        self, reason: str, identifier: str, details: dict[str, object] | None = None
    ):
        self.code = f"error.booklet_background_{reason}"
        super().__init__(identifier, details)


class BookletPageRenderTimeout(AppError):
    message = "The booklet page took too long to render"
    code = "error.booklet_page_render_timeout"
    status_code = 503


class ExportRenderTimeout(AppError):
    message = "The export took too long to render"
    code = "error.export_render_timeout"
    status_code = 503


class StorageFileTooLarge(AppError):
    message = "The uploaded file is too large"
    code = "error.storage_file_too_large"
    status_code = 400


class StorageImageTooLarge(AppError):
    message = "The uploaded image has too many pixels"
    code = "error.storage_image_too_large"
    status_code = 400


class StorageFileInvalidMimeType(AppError):
    message = "The uploaded file type is not allowed"
    code = "error.storage_file_invalid_mime_type"
    status_code = 400


class KpRequirementFileUploadNotAllowed(AppError):
    message = "This requirement does not accept file uploads"
    code = "error.kp_requirement_file_upload_not_allowed"
    status_code = 400


class KpRequirementTextAnswerNotAllowed(AppError):
    message = "This requirement does not accept text answers"
    code = "error.kp_requirement_text_answer_not_allowed"
    status_code = 400


class MailTemplateNotFound(AppError):
    message = "Mail template not found"
    code = "error.mail_template_not_found"
    status_code = 404


class MailTemplateInvalid(AppError):
    code = "error.mail_template_invalid"
    status_code = 400

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
        self.message = f"Mail template is invalid: {detail}"
        super().__init__(identifier, details)


class MailCampaignNotFound(AppError):
    message = "Mail campaign not found"
    code = "error.mail_campaign_not_found"
    status_code = 404


class MailCampaignLocked(AppError):
    message = "The mail campaign can no longer be changed in its current state"
    code = "error.mail_campaign_locked"
    status_code = 409


class MailCampaignScheduleInPast(AppError):
    message = "The mail campaign has to be scheduled in the future"
    code = "error.mail_campaign_schedule_in_past"
    status_code = 400


class KeycloakExchangeFailed(AppError):
    message = "Keycloak exchange failed"
    code = "error.keycloak_exchange_failed"
    status_code = 400


class TokenInvalid(AppError):
    message = "Token is invalid"
    code = "error.token_invalid"
    status_code = 400


class NotAllowed(AppError):
    message = "User is not allowed to make this request"
    code = "error.not_allowed"
    status_code = 403


class EmailNotConfirmed(AppError):
    message = "User email is not confirmed"
    code = "error.email_not_confirmed"
    status_code = 403


class CompanyNotConfirmed(AppError):
    message = "Company is not confirmed by VIS yet"
    code = "error.company_not_confirmed"
    status_code = 403


class PhoneNumberInvalid(AppError):
    message = "Phone number is invalid"
    code = "error.phone_number_invalid"
    status_code = 400


class InvalidCredentials(AppError):
    message = "Invalid credentials"
    code = "error.invalid_credentials"
    status_code = 400


class EmailUsed(AppError):
    message = "Email is already used"
    code = "error.email_used"
    status_code = 400


class EmailTakenLocally(AppError):
    message = "Email already belongs to a local account"
    code = "auth.email_taken_locally"
    status_code = 403


class NotVisMember(AppError):
    message = "User has no active VIS membership role"
    code = "auth.not_vis_member"
    status_code = 403


class PasswordTooShort(AppError):
    message = "Password is too short"
    code = "error.password_too_short"
    status_code = 400


class ResetPasswordError(AppError):
    message = "Password reset failed"
    code = "error.reset_password_failed"
    status_code = 400


class InviteNotFound(AppError):
    message = "Invite not found or already used"
    code = "error.invite_not_found"
    status_code = 404


class InviteExpired(AppError):
    message = "Invite has expired"
    code = "error.invite_expired"
    status_code = 400


class InviteEmailMismatch(AppError):
    message = "Invite was issued for a different email address"
    code = "error.invite_email_mismatch"
    status_code = 403


class RateLimited(AppError):
    message = "Too many requests, please try again later"
    code = "error.rate_limited"
    status_code = 429


class CsrfInvalid(AppError):
    message = "CSRF validation failed"
    code = "csrf.validation_failed"
    status_code = 403
