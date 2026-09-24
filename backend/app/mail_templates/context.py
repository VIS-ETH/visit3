from dataclasses import dataclass, fields

from app.mail_templates.keys import MailTemplateKey


@dataclass(frozen=True)
class MailContext:
    def variables(self) -> dict[str, str]:
        return {field.name: getattr(self, field.name) for field in fields(self)}

    @classmethod
    def variable_names(cls) -> frozenset[str]:
        return frozenset(field.name for field in fields(cls))


@dataclass(frozen=True)
class AccountConfirmEmailContext(MailContext):
    name: str
    confirm_url: str


@dataclass(frozen=True)
class AccountConfirmedContext(MailContext):
    name: str
    login_url: str


@dataclass(frozen=True)
class AccountAwaitingConfirmationContext(MailContext):
    name: str
    email: str
    admin_url: str


@dataclass(frozen=True)
class PasswordResetContext(MailContext):
    name: str
    reset_url: str


@dataclass(frozen=True)
class CompanyInviteContext(MailContext):
    company_name: str
    invite_url: str


@dataclass(frozen=True)
class BookingContext(MailContext):
    name: str
    company_name: str
    event_name: str
    booth_zone_name: str
    login_url: str


@dataclass(frozen=True)
class BookingAcceptedContext(BookingContext):
    booth_number: str


@dataclass(frozen=True)
class BookingRejectedContext(BookingContext):
    reason: str


@dataclass(frozen=True)
class BookingReminderContext(BookingContext):
    finalization_deadline: str


SAMPLE_CONTEXTS: dict[MailTemplateKey, MailContext] = {
    MailTemplateKey.ACCOUNT_CONFIRM_EMAIL: AccountConfirmEmailContext(
        name="Ada Lovelace",
        confirm_url="https://visit.vis.ethz.ch/confirm-email/sample-token",
    ),
    MailTemplateKey.ACCOUNT_CONFIRMED: AccountConfirmedContext(
        name="Ada Lovelace",
        login_url="https://visit.vis.ethz.ch/auth/link/sample-token",
    ),
    MailTemplateKey.ACCOUNT_AWAITING_CONFIRMATION: AccountAwaitingConfirmationContext(
        name="Ada Lovelace",
        email="ada@example.com",
        admin_url="https://visit.vis.ethz.ch/user-management",
    ),
    MailTemplateKey.PASSWORD_RESET: PasswordResetContext(
        name="Ada Lovelace",
        reset_url="https://visit.vis.ethz.ch/reset/sample-token",
    ),
    MailTemplateKey.COMPANY_INVITE: CompanyInviteContext(
        company_name="Acme AG",
        invite_url=(
            "https://visit.vis.ethz.ch/company/join/sample-token"
            "?email=ada%40example.com"
        ),
    ),
    MailTemplateKey.BOOKING_REGISTERED: BookingContext(
        name="Ada Lovelace",
        company_name="Acme AG",
        event_name="Kontaktparty 2026",
        booth_zone_name="Haupthalle",
        login_url="https://visit.vis.ethz.ch/auth/link/sample-token",
    ),
    MailTemplateKey.BOOKING_ACCEPTED: BookingAcceptedContext(
        name="Ada Lovelace",
        company_name="Acme AG",
        event_name="Kontaktparty 2026",
        booth_zone_name="Haupthalle",
        login_url="https://visit.vis.ethz.ch/auth/link/sample-token",
        booth_number="12",
    ),
    MailTemplateKey.BOOKING_REJECTED: BookingRejectedContext(
        name="Ada Lovelace",
        company_name="Acme AG",
        event_name="Kontaktparty 2026",
        booth_zone_name="Haupthalle",
        login_url="https://visit.vis.ethz.ch/auth/link/sample-token",
        reason="Die Standzone ist ausgebucht.",
    ),
    MailTemplateKey.BOOKING_INCOMPLETE_REMINDER: BookingReminderContext(
        name="Ada Lovelace",
        company_name="Acme AG",
        event_name="Kontaktparty 2026",
        booth_zone_name="Haupthalle",
        login_url="https://visit.vis.ethz.ch/auth/link/sample-token",
        finalization_deadline="2026-10-01",
    ),
    MailTemplateKey.WAITLIST_PROMOTED: BookingContext(
        name="Ada Lovelace",
        company_name="Acme AG",
        event_name="Kontaktparty 2026",
        booth_zone_name="Haupthalle",
        login_url="https://visit.vis.ethz.ch/auth/link/sample-token",
    ),
}


def allowed_variables(key: MailTemplateKey) -> frozenset[str]:
    return type(SAMPLE_CONTEXTS[key]).variable_names()
