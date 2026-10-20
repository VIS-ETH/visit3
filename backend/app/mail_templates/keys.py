from enum import StrEnum


class MailTemplateKey(StrEnum):
    ACCOUNT_CONFIRM_EMAIL = "account_confirm_email"
    PASSWORD_RESET = "password_reset"
    ACCOUNT_EXISTS = "account_exists"
    EMAIL_CHANGE_CONFIRM = "email_change_confirm"
    EMAIL_CHANGE_NOTICE = "email_change_notice"
    EMAIL_CHANGED = "email_changed"
    COMPANY_INVITE = "company_invite"
    COMPANY_CONFIRMED = "company_confirmed"
    COMPANY_AWAITING_CONFIRMATION = "company_awaiting_confirmation"
    BOOKING_REGISTERED = "booking_registered"
    BOOKING_ACCEPTED = "booking_accepted"
    BOOKING_REJECTED = "booking_rejected"
    BOOKING_INCOMPLETE_REMINDER = "booking_incomplete_reminder"
    WAITLIST_PROMOTED = "waitlist_promoted"
    BOOKING_OFFERED = "booking_offered"
    BOOKING_OFFER_WEEK_REMINDER = "booking_offer_week_reminder"
    BOOKING_OFFER_DAY_REMINDER = "booking_offer_day_reminder"
