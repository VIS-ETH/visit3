from app.mail_templates.keys import MailTemplateKey
from app.mail_templates.texts import MailTemplateTexts

MAIL_TEMPLATE_DEFAULTS: dict[MailTemplateKey, MailTemplateTexts] = {
    MailTemplateKey.ACCOUNT_CONFIRM_EMAIL: MailTemplateTexts(
        subject_de="VISIT: E-Mail-Adresse bestätigen",
        subject_en="VISIT: Confirm your email address",
        body_de=(
            "<p>Hallo {{ name }},</p>"
            "<p>bitte bestätigen Sie Ihre E-Mail-Adresse, damit wir Ihr VISIT-Konto"
            " freischalten können.</p>"
            '<p><a href="{{ confirm_url }}">E-Mail-Adresse bestätigen</a></p>'
            "<p>Viele Grüsse<br />Ihr VIS-Kontaktparty-Team</p>"
        ),
        body_en=(
            "<p>Hello {{ name }},</p>"
            "<p>please confirm your email address so that we can activate your"
            " VISIT account.</p>"
            '<p><a href="{{ confirm_url }}">Confirm email address</a></p>'
            "<p>Best regards<br />Your VIS Kontaktparty team</p>"
        ),
    ),
    MailTemplateKey.ACCOUNT_CONFIRMED: MailTemplateTexts(
        subject_de="VISIT: Konto freigeschaltet",
        subject_en="VISIT: Account activated",
        body_de=(
            "<p>Hallo {{ name }},</p>"
            "<p>Ihr VISIT-Konto wurde vom VIS freigegeben. Sie können sich ab sofort"
            " anmelden und Ihr Unternehmen verwalten.</p>"
            '<p><a href="{{ login_url }}">Zu VISIT</a></p>'
            "<p>Viele Grüsse<br />Ihr VIS-Kontaktparty-Team</p>"
        ),
        body_en=(
            "<p>Hello {{ name }},</p>"
            "<p>your VISIT account has been approved by VIS. You can log in and manage"
            " your company from now on.</p>"
            '<p><a href="{{ login_url }}">Go to VISIT</a></p>'
            "<p>Best regards<br />Your VIS Kontaktparty team</p>"
        ),
    ),
    MailTemplateKey.ACCOUNT_AWAITING_CONFIRMATION: MailTemplateTexts(
        subject_de="VISIT: Neues Konto wartet auf Freigabe",
        subject_en="VISIT: New account awaiting approval",
        body_de=(
            "<p>{{ name }} ({{ email }}) hat die E-Mail-Adresse bestätigt und wartet"
            " nun auf die Freigabe durch den VIS.</p>"
            '<p><a href="{{ admin_url }}">Konto prüfen</a></p>'
        ),
        body_en=(
            "<p>{{ name }} ({{ email }}) confirmed their email address and is now"
            " waiting for approval by VIS.</p>"
            '<p><a href="{{ admin_url }}">Review account</a></p>'
        ),
    ),
    MailTemplateKey.PASSWORD_RESET: MailTemplateTexts(
        subject_de="VISIT: Passwort zurücksetzen",
        subject_en="VISIT: Reset your password",
        body_de=(
            "<p>Hallo {{ name }},</p>"
            "<p>über den folgenden Link können Sie ein neues Passwort für VISIT"
            " setzen. Der Link ist zehn Minuten gültig.</p>"
            '<p><a href="{{ reset_url }}">Passwort zurücksetzen</a></p>'
            "<p>Wenn Sie kein neues Passwort angefordert haben, können Sie diese"
            " Nachricht ignorieren.</p>"
        ),
        body_en=(
            "<p>Hello {{ name }},</p>"
            "<p>use the following link to set a new password for VISIT. The link is"
            " valid for ten minutes.</p>"
            '<p><a href="{{ reset_url }}">Reset password</a></p>'
            "<p>If you did not request a new password, you can ignore this"
            " message.</p>"
        ),
    ),
    MailTemplateKey.COMPANY_INVITE: MailTemplateTexts(
        subject_de="VISIT: Einladung zu {{ company_name }}",
        subject_en="VISIT: Invitation to join {{ company_name }}",
        body_de=(
            "<p>Sie wurden eingeladen, dem Unternehmen {{ company_name }} auf VISIT"
            " beizutreten.</p>"
            '<p><a href="{{ invite_url }}">Einladung annehmen</a></p>'
            "<p>Die Einladung ist sieben Tage gültig.</p>"
        ),
        body_en=(
            "<p>You have been invited to join the company {{ company_name }} on"
            " VISIT.</p>"
            '<p><a href="{{ invite_url }}">Accept invitation</a></p>'
            "<p>The invitation is valid for seven days.</p>"
        ),
    ),
    MailTemplateKey.BOOKING_REGISTERED: MailTemplateTexts(
        subject_de="VISIT: Anmeldung für {{ event_name }} erhalten",
        subject_en="VISIT: Registration for {{ event_name }} received",
        body_de=(
            "<p>Hallo {{ name }},</p>"
            "<p>wir haben die Anmeldung von {{ company_name }} für {{ event_name }}"
            " in der Standzone {{ booth_zone_name }} erhalten.</p>"
            "<p>Bitte vervollständigen Sie Ihre Buchung rechtzeitig vor dem"
            " Stichtag.</p>"
            '<p><a href="{{ login_url }}">Buchung öffnen</a></p>'
        ),
        body_en=(
            "<p>Hello {{ name }},</p>"
            "<p>we received the registration of {{ company_name }} for"
            " {{ event_name }} in booth zone {{ booth_zone_name }}.</p>"
            "<p>Please complete your booking before the deadline.</p>"
            '<p><a href="{{ login_url }}">Open booking</a></p>'
        ),
    ),
    MailTemplateKey.BOOKING_FINALIZED: MailTemplateTexts(
        subject_de="VISIT: Buchung für {{ event_name }} abgeschlossen",
        subject_en="VISIT: Booking for {{ event_name }} completed",
        body_de=(
            "<p>Hallo {{ name }},</p>"
            "<p>{{ company_name }} hat die Buchung für {{ event_name }} in der"
            " Standzone {{ booth_zone_name }} abgeschlossen.</p>"
            "<p>Gesamtbetrag: {{ total_price }}</p>"
            "<p>Der VIS prüft die Buchung und meldet sich bei Ihnen.</p>"
            '<p><a href="{{ login_url }}">Buchung öffnen</a></p>'
        ),
        body_en=(
            "<p>Hello {{ name }},</p>"
            "<p>{{ company_name }} completed the booking for {{ event_name }} in booth"
            " zone {{ booth_zone_name }}.</p>"
            "<p>Total amount: {{ total_price }}</p>"
            "<p>VIS will review the booking and get back to you.</p>"
            '<p><a href="{{ login_url }}">Open booking</a></p>'
        ),
    ),
    MailTemplateKey.BOOKING_ACCEPTED: MailTemplateTexts(
        subject_de="VISIT: Buchung für {{ event_name }} bestätigt",
        subject_en="VISIT: Booking for {{ event_name }} confirmed",
        body_de=(
            "<p>Hallo {{ name }},</p>"
            "<p>die Buchung von {{ company_name }} für {{ event_name }} wurde"
            " bestätigt.</p>"
            "<p>Standzone: {{ booth_zone_name }}<br />"
            "Standnummer: {{ booth_number }}</p>"
            '<p><a href="{{ login_url }}">Buchung öffnen</a></p>'
        ),
        body_en=(
            "<p>Hello {{ name }},</p>"
            "<p>the booking of {{ company_name }} for {{ event_name }} has been"
            " confirmed.</p>"
            "<p>Booth zone: {{ booth_zone_name }}<br />"
            "Booth number: {{ booth_number }}</p>"
            '<p><a href="{{ login_url }}">Open booking</a></p>'
        ),
    ),
    MailTemplateKey.BOOKING_REJECTED: MailTemplateTexts(
        subject_de="VISIT: Buchung für {{ event_name }} abgelehnt",
        subject_en="VISIT: Booking for {{ event_name }} rejected",
        body_de=(
            "<p>Hallo {{ name }},</p>"
            "<p>die Buchung von {{ company_name }} für {{ event_name }} in der"
            " Standzone {{ booth_zone_name }} wurde leider abgelehnt.</p>"
            "<p>Begründung: {{ reason }}</p>"
            '<p><a href="{{ login_url }}">Buchung öffnen</a></p>'
        ),
        body_en=(
            "<p>Hello {{ name }},</p>"
            "<p>unfortunately the booking of {{ company_name }} for {{ event_name }}"
            " in booth zone {{ booth_zone_name }} has been rejected.</p>"
            "<p>Reason: {{ reason }}</p>"
            '<p><a href="{{ login_url }}">Open booking</a></p>'
        ),
    ),
    MailTemplateKey.BOOKING_INCOMPLETE_REMINDER: MailTemplateTexts(
        subject_de="VISIT: Buchung für {{ event_name }} ist unvollständig",
        subject_en="VISIT: Your booking for {{ event_name }} is incomplete",
        body_de=(
            "<p>Hallo {{ name }},</p>"
            "<p>die Buchung von {{ company_name }} für {{ event_name }} in der"
            " Standzone {{ booth_zone_name }} ist noch nicht abgeschlossen.</p>"
            "<p>Bitte vervollständige sie bis zum {{ finalization_deadline }}.</p>"
            '<p><a href="{{ login_url }}">Buchung öffnen</a></p>'
        ),
        body_en=(
            "<p>Hello {{ name }},</p>"
            "<p>the booking of {{ company_name }} for {{ event_name }} in booth zone"
            " {{ booth_zone_name }} is not complete yet.</p>"
            "<p>Please complete it by {{ finalization_deadline }}.</p>"
            '<p><a href="{{ login_url }}">Open booking</a></p>'
        ),
    ),
    MailTemplateKey.WAITLIST_PROMOTED: MailTemplateTexts(
        subject_de="VISIT: Platz in {{ booth_zone_name }} frei geworden",
        subject_en="VISIT: A spot in {{ booth_zone_name }} became available",
        body_de=(
            "<p>Hallo {{ name }},</p>"
            "<p>{{ company_name }} rückt für {{ event_name }} von der Warteliste in"
            " die Standzone {{ booth_zone_name }} nach.</p>"
            '<p><a href="{{ login_url }}">Buchung öffnen</a></p>'
        ),
        body_en=(
            "<p>Hello {{ name }},</p>"
            "<p>{{ company_name }} moved up from the waitlist into booth zone"
            " {{ booth_zone_name }} for {{ event_name }}.</p>"
            '<p><a href="{{ login_url }}">Open booking</a></p>'
        ),
    ),
}
