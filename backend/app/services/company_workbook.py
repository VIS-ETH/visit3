from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from zoneinfo import ZoneInfo

from app.core.rich_text import rich_text_plain
from app.models.company import KpCompanyLanguage
from app.models.kp_event import (
    KpBookingCompanyDetails,
    KpBookingStatus,
    KpEvent,
    KpEventBooking,
)
from app.models.user import User
from app.services.booking_completeness import (
    BILLING_ADDRESS_MISSING,
    COMPANY_DESCRIPTION_MISSING,
    COMPANY_PROFILE_MISSING,
    GENERAL_EMAIL_MISSING,
    booking_completeness,
)
from app.services.pricing import price_breakdown
from app.services.xlsx_service import CellValue, ColumnKind, XlsxColumn, XlsxSheet

LOCAL_TIMEZONE = ZoneInfo("Europe/Zurich")
REQUIREMENT_PREFIX = "requirement:"


class ExportLanguage(str, Enum):
    DE = "de"
    EN = "en"


@dataclass(frozen=True)
class Labels:
    companies_sheet: str
    contacts_sheet: str
    yes: str
    no: str
    statuses: dict[KpBookingStatus, str]
    languages: dict[KpCompanyLanguage, str]
    missing_items: dict[str, str]
    company_columns: tuple[str, ...]
    contact_columns: tuple[str, ...]


LABELS: dict[ExportLanguage, Labels] = {
    ExportLanguage.DE: Labels(
        companies_sheet="Unternehmen",
        contacts_sheet="Kontakte",
        yes="Ja",
        no="Nein",
        statuses={
            KpBookingStatus.REGISTERED: "Registriert",
            KpBookingStatus.CONFIRMED: "Bestätigt",
            KpBookingStatus.CANCELLED: "Storniert",
            KpBookingStatus.REJECTED: "Abgelehnt",
        },
        languages={
            KpCompanyLanguage.GERMAN: "Deutsch",
            KpCompanyLanguage.ENGLISH: "Englisch",
            KpCompanyLanguage.FRENCH: "Französisch",
            KpCompanyLanguage.ITALIAN: "Italienisch",
        },
        missing_items={
            COMPANY_PROFILE_MISSING: "Unternehmensprofil",
            COMPANY_DESCRIPTION_MISSING: "Unternehmensbeschreibung",
            BILLING_ADDRESS_MISSING: "Rechnungsadresse",
            GENERAL_EMAIL_MISSING: "Allgemeine E-Mail",
        },
        company_columns=(
            "Unternehmen",
            "Marke",
            "Status",
            "Zone",
            "Stand-Nr.",
            "Standfläche (m²)",
            "Buchungs-Nr.",
            "Registriert am",
            "Bestätigt am",
            "Kontaktperson",
            "E-Mail Kontaktperson",
            "Telefon Kontaktperson",
            "Allgemeine E-Mail",
            "Allgemeine Telefonnummer",
            "Website",
            "Rechnungsempfänger",
            "Rechnungsadresse",
            "PLZ",
            "Ort",
            "Land",
            "MWST-Nr.",
            "Rechnungs-E-Mail",
            "Services",
            "Namensschilder",
            "Netto",
            "MWST",
            "Brutto",
            "Fehlende Angaben",
            "Beschreibung",
            "Branchen",
            "Sprachen",
            "Arbeitsorte",
            "Mitarbeitende Schweiz",
            "Mitarbeitende weltweit",
            "Praktika",
            "Teilzeitstellen",
            "Abschlussarbeiten",
            "Einstiegsstellen",
        ),
        contact_columns=(
            "Unternehmen",
            "Status",
            "Zone",
            "Stand-Nr.",
            "Vorname",
            "Nachname",
            "E-Mail",
            "Telefon",
            "Kontaktperson",
        ),
    ),
    ExportLanguage.EN: Labels(
        companies_sheet="Companies",
        contacts_sheet="Contacts",
        yes="Yes",
        no="No",
        statuses={
            KpBookingStatus.REGISTERED: "Registered",
            KpBookingStatus.CONFIRMED: "Confirmed",
            KpBookingStatus.CANCELLED: "Cancelled",
            KpBookingStatus.REJECTED: "Rejected",
        },
        languages={
            KpCompanyLanguage.GERMAN: "German",
            KpCompanyLanguage.ENGLISH: "English",
            KpCompanyLanguage.FRENCH: "French",
            KpCompanyLanguage.ITALIAN: "Italian",
        },
        missing_items={
            COMPANY_PROFILE_MISSING: "Company profile",
            COMPANY_DESCRIPTION_MISSING: "Company description",
            BILLING_ADDRESS_MISSING: "Billing address",
            GENERAL_EMAIL_MISSING: "General email",
        },
        company_columns=(
            "Company",
            "Brand",
            "Status",
            "Zone",
            "Booth no.",
            "Booth size (m²)",
            "Booking no.",
            "Registered on",
            "Confirmed on",
            "Contact person",
            "Contact person email",
            "Contact person phone",
            "General email",
            "General phone",
            "Website",
            "Billing recipient",
            "Billing address",
            "Postal code",
            "City",
            "Country",
            "VAT no.",
            "Billing email",
            "Services",
            "Name tags",
            "Net",
            "VAT",
            "Gross",
            "Missing items",
            "Description",
            "Industries",
            "Languages",
            "Places of work",
            "Employees Switzerland",
            "Employees worldwide",
            "Internships",
            "Part-time positions",
            "Theses",
            "Graduate positions",
        ),
        contact_columns=(
            "Company",
            "Status",
            "Zone",
            "Booth no.",
            "First name",
            "Last name",
            "Email",
            "Phone",
            "Contact person",
        ),
    ),
}

COMPANY_KINDS: tuple[ColumnKind, ...] = (
    "text",
    "text",
    "text",
    "text",
    "integer",
    "number",
    "integer",
    "datetime",
    "datetime",
    "text",
    "text",
    "text",
    "text",
    "text",
    "text",
    "text",
    "text",
    "text",
    "text",
    "text",
    "text",
    "text",
    "long_text",
    "integer",
    "money",
    "money",
    "money",
    "long_text",
    "long_text",
    "text",
    "text",
    "text",
    "integer",
    "integer",
    "text",
    "text",
    "text",
    "text",
)
CONTACT_KINDS: tuple[ColumnKind, ...] = (
    "text",
    "text",
    "text",
    "integer",
    "text",
    "text",
    "text",
    "text",
    "text",
)


def _columns(headers: Sequence[str], kinds: Sequence[ColumnKind]) -> list[XlsxColumn]:
    return [
        XlsxColumn(header, kind) for header, kind in zip(headers, kinds, strict=True)
    ]


def _local(moment: datetime | None) -> datetime | None:
    if moment is None:
        return None
    if moment.tzinfo is None:
        return moment
    return moment.astimezone(LOCAL_TIMEZONE).replace(tzinfo=None)


def _francs(cents: int) -> float:
    return cents / 100


def _joined(*parts: str | None) -> str:
    return " ".join(part.strip() for part in parts if part and part.strip())


def _full_name(user: User | None) -> str | None:
    if user is None:
        return None
    return _joined(user.first_name, user.last_name) or user.email


def _requirement_names(booking: KpEventBooking) -> dict[str, str]:
    return {
        str(requirement.id): f"{booking_service.service.name} · {requirement.name}"
        for booking_service in booking.services
        for requirement in booking_service.service.requirements
    }


def _missing_items(booking: KpEventBooking, labels: Labels) -> str:
    requirement_names = _requirement_names(booking)
    return "\n".join(
        requirement_names.get(item.removeprefix(REQUIREMENT_PREFIX), item)
        if item.startswith(REQUIREMENT_PREFIX)
        else labels.missing_items.get(item, item)
        for item in booking_completeness(booking)
    )


def _services(booking: KpEventBooking) -> str:
    return "\n".join(
        f"{booking_service.service.name} × {booking_service.quantity}"
        for booking_service in booking.services
    )


def _details_cells(
    details: KpBookingCompanyDetails | None, labels: Labels
) -> dict[str, CellValue]:
    if details is None:
        return {}

    def yes_no(value: bool) -> str:
        return labels.yes if value else labels.no

    return {
        "brand": details.brand_name,
        "website": details.website,
        "billing_recipient": details.billing_company_name,
        "billing_address": _joined(
            details.billing_street, details.billing_house_number
        ),
        "postal_code": details.billing_postal_code,
        "city": details.billing_city,
        "country": details.billing_country,
        "vat_number": details.billing_vat_number,
        "billing_email": details.billing_email,
        "description": rich_text_plain(details.description),
        "industries": ", ".join(sorted(details.industry_names)),
        "languages": ", ".join(
            labels.languages[KpCompanyLanguage(language)]
            for language in details.languages
        ),
        "places_of_work": details.places_of_work,
        "employees_switzerland": details.employee_count_switzerland,
        "employees_worldwide": details.employee_count_worldwide,
        "internships": yes_no(details.offers_internships),
        "part_time": yes_no(details.offers_part_time),
        "theses": yes_no(details.offers_theses),
        "graduate_positions": yes_no(details.offers_graduate_positions),
    }


def _company_row(
    booking: KpEventBooking, event: KpEvent, labels: Labels
) -> list[CellValue]:
    profile = booking.company.kp_profile
    contact = profile.kp_contact_user if profile is not None else None
    details = _details_cells(booking.company_details, labels)
    prices = price_breakdown(booking.total_price, event.vat_rate_permille)
    return [
        booking.company.name,
        details.get("brand"),
        labels.statuses[booking.status],
        booking.booth_zone.name,
        booking.booth_nr,
        booking.booth_zone.booth_size,
        booking.booking_number,
        _local(booking.created_at),
        _local(booking.confirmed_at),
        _full_name(contact),
        contact.email if contact is not None else None,
        contact.phone_number if contact is not None else None,
        profile.general_email if profile is not None else None,
        profile.general_phone if profile is not None else None,
        details.get("website"),
        details.get("billing_recipient"),
        details.get("billing_address"),
        details.get("postal_code"),
        details.get("city"),
        details.get("country"),
        details.get("vat_number"),
        details.get("billing_email"),
        _services(booking),
        len(booking.name_tags),
        _francs(prices.net),
        _francs(prices.vat),
        _francs(prices.gross),
        _missing_items(booking, labels),
        details.get("description"),
        details.get("industries"),
        details.get("languages"),
        details.get("places_of_work"),
        details.get("employees_switzerland"),
        details.get("employees_worldwide"),
        details.get("internships"),
        details.get("part_time"),
        details.get("theses"),
        details.get("graduate_positions"),
    ]


def _contact_rows(booking: KpEventBooking, labels: Labels) -> list[list[CellValue]]:
    profile = booking.company.kp_profile
    contact_id = profile.kp_contact_user_id if profile is not None else None
    members = sorted(
        booking.company.users,
        key=lambda user: (
            (user.last_name or "").casefold(),
            (user.first_name or "").casefold(),
            user.email,
        ),
    )
    return [
        [
            booking.company.name,
            labels.statuses[booking.status],
            booking.booth_zone.name,
            booking.booth_nr,
            member.first_name,
            member.last_name,
            member.email,
            member.phone_number,
            labels.yes if member.id == contact_id else labels.no,
        ]
        for member in members
    ]


def _booking_order(booking: KpEventBooking) -> tuple[object, ...]:
    return (
        not booking.is_active,
        booking.booth_zone.order,
        booking.booth_zone.name.casefold(),
        booking.booth_nr is None,
        booking.booth_nr or 0,
        booking.company.name.casefold(),
    )


def company_workbook_sheets(
    event: KpEvent, bookings: Sequence[KpEventBooking], language: ExportLanguage
) -> list[XlsxSheet]:
    labels = LABELS[language]
    ordered = sorted(bookings, key=_booking_order)
    return [
        XlsxSheet(
            labels.companies_sheet,
            _columns(labels.company_columns, COMPANY_KINDS),
            [_company_row(booking, event, labels) for booking in ordered],
        ),
        XlsxSheet(
            labels.contacts_sheet,
            _columns(labels.contact_columns, CONTACT_KINDS),
            [
                row
                for booking in ordered
                if booking.is_active
                for row in _contact_rows(booking, labels)
            ],
        ),
    ]


def company_workbook_filename(event: KpEvent, language: ExportLanguage) -> str:
    label = LABELS[language].companies_sheet
    return f"{event.name} {label} {date.today().isoformat()}.xlsx"
