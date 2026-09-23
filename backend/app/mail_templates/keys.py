from enum import StrEnum


class MailTemplateKey(StrEnum):
    ACCOUNT_CONFIRM_EMAIL = "account_confirm_email"
    ACCOUNT_CONFIRMED = "account_confirmed"
    ACCOUNT_AWAITING_CONFIRMATION = "account_awaiting_confirmation"
    PASSWORD_RESET = "password_reset"
    COMPANY_INVITE = "company_invite"
    BOOKING_REGISTERED = "booking_registered"
    BOOKING_FINALIZED = "booking_finalized"
    BOOKING_ACCEPTED = "booking_accepted"
    BOOKING_REJECTED = "booking_rejected"
    BOOKING_INCOMPLETE_REMINDER = "booking_incomplete_reminder"
    WAITLIST_PROMOTED = "waitlist_promoted"
