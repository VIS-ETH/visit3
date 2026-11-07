from typing import Annotated

from fastapi import Depends

from app.core.config import get_settings
from app.core.deps.auth import CurrentUserDep
from app.core.deps.database import SessionLocal
from app.core.deps.repositories import (
    ChangeRepositoryDep,
    CompanyRepositoryDep,
    IndustryRepositoryDep,
    KpRepositoryDep,
    MailCampaignRepositoryDep,
    MailTemplateRepositoryDep,
    RoleRepositoryDep,
    TokenRepositoryDep,
    UserRepositoryDep,
    VenueRepositoryDep,
)
from app.core.grpc import grpc_client
from app.generated.sip.notifications.mail_pb2_grpc import MailServiceStub
from app.services.auth_service import AuthService
from app.services.booking_notifier import MailBookingNotifier
from app.services.booklet_service import BookletService
from app.services.change_service import ChangeService
from app.services.company_service import CompanyService
from app.services.csv_service import CsvService
from app.services.event_banner_service import EventBannerService
from app.services.export_service import ExportService
from app.services.industry_service import IndustryService
from app.services.invite_service import InviteService
from app.services.kp_service import KpService
from app.services.mail_campaign_delivery import MailCampaignDelivery, SessionFactory
from app.services.mail_campaign_service import MailCampaignService
from app.services.mail_service import MailService
from app.services.mail_template_admin_service import MailTemplateAdminService
from app.services.mail_template_service import MailTemplateService
from app.services.notification_recipients import NotificationRecipients
from app.services.pdf_service import PdfService
from app.services.storage_service import StorageService
from app.services.user_service import UserService
from app.services.venue_service import VenueService
from app.services.xlsx_service import XlsxService


async def get_stub():
    return grpc_client.stub


MailDep = Annotated[MailServiceStub, Depends(get_stub)]


async def get_mail_service(mail: MailDep):
    return MailService(mail)


MailServiceDep = Annotated[MailService, Depends(get_mail_service)]


async def get_notification_recipients(
    kp_repository: KpRepositoryDep,
):
    return NotificationRecipients(kp_repository)


NotificationRecipientsDep = Annotated[
    NotificationRecipients, Depends(get_notification_recipients)
]


async def get_mail_template_service(
    mail_template_repository: MailTemplateRepositoryDep,
    notification_recipients: NotificationRecipientsDep,
    mail_service: MailServiceDep,
):
    return MailTemplateService(
        mail_template_repository, notification_recipients, mail_service
    )


MailTemplateServiceDep = Annotated[
    MailTemplateService, Depends(get_mail_template_service)
]


async def get_mail_template_admin_service(
    mail_template_repository: MailTemplateRepositoryDep,
    mail_template_service: MailTemplateServiceDep,
    current_user: CurrentUserDep,
):
    return MailTemplateAdminService(
        mail_template_repository, mail_template_service, current_user
    )


MailTemplateAdminServiceDep = Annotated[
    MailTemplateAdminService, Depends(get_mail_template_admin_service)
]


async def get_invite_service(company_repository: CompanyRepositoryDep):
    return InviteService(company_repository)


InviteServiceDep = Annotated[InviteService, Depends(get_invite_service)]


async def get_auth_service(
    user_repository: UserRepositoryDep,
    token_repository: TokenRepositoryDep,
    role_repository: RoleRepositoryDep,
    mail_template_service: MailTemplateServiceDep,
    invite_service: InviteServiceDep,
):
    return AuthService(
        user_repository,
        token_repository,
        role_repository,
        mail_template_service,
        invite_service,
    )


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


async def get_user_service(
    user_repository: UserRepositoryDep,
    token_repository: TokenRepositoryDep,
    company_repository: CompanyRepositoryDep,
    auth_service: AuthServiceDep,
    mail_template_service: MailTemplateServiceDep,
    current_user: CurrentUserDep,
):
    return UserService(
        user_repository,
        token_repository,
        company_repository,
        auth_service,
        mail_template_service,
        current_user,
    )


UserServiceDep = Annotated[UserService, Depends(get_user_service)]


def get_storage_service():
    return StorageService(get_settings())


StorageServiceDep = Annotated[StorageService, Depends(get_storage_service)]


async def get_company_service(
    company_repository: CompanyRepositoryDep,
    mail_template_service: MailTemplateServiceDep,
    storage_service: StorageServiceDep,
    current_user: CurrentUserDep,
):
    return CompanyService(
        company_repository, mail_template_service, storage_service, current_user
    )


CompanyServiceDep = Annotated[CompanyService, Depends(get_company_service)]


async def get_industry_service(
    industry_repository: IndustryRepositoryDep,
    current_user: CurrentUserDep,
):
    return IndustryService(industry_repository, current_user)


IndustryServiceDep = Annotated[IndustryService, Depends(get_industry_service)]


async def get_change_service(
    change_repository: ChangeRepositoryDep,
    current_user: CurrentUserDep,
):
    return ChangeService(change_repository, current_user)


ChangeServiceDep = Annotated[ChangeService, Depends(get_change_service)]


async def get_booking_notifier(
    mail_template_service: MailTemplateServiceDep,
    auth_service: AuthServiceDep,
):
    return MailBookingNotifier(mail_template_service, auth_service)


BookingNotifierDep = Annotated[MailBookingNotifier, Depends(get_booking_notifier)]


async def get_kp_service(
    kp_repository: KpRepositoryDep,
    storage_service: StorageServiceDep,
    current_user: CurrentUserDep,
    booking_notifier: BookingNotifierDep,
):
    return KpService(kp_repository, storage_service, current_user, booking_notifier)


KpServiceDep = Annotated[KpService, Depends(get_kp_service)]


async def get_venue_service(
    venue_repository: VenueRepositoryDep,
    kp_repository: KpRepositoryDep,
    storage_service: StorageServiceDep,
    current_user: CurrentUserDep,
):
    return VenueService(venue_repository, kp_repository, storage_service, current_user)


VenueServiceDep = Annotated[VenueService, Depends(get_venue_service)]


def get_pdf_service():
    return PdfService()


PdfServiceDep = Annotated[PdfService, Depends(get_pdf_service)]


def get_csv_service():
    return CsvService()


CsvServiceDep = Annotated[CsvService, Depends(get_csv_service)]


def get_xlsx_service():
    return XlsxService()


XlsxServiceDep = Annotated[XlsxService, Depends(get_xlsx_service)]


async def get_export_service(
    kp_repository: KpRepositoryDep,
    storage_service: StorageServiceDep,
    pdf_service: PdfServiceDep,
    csv_service: CsvServiceDep,
    xlsx_service: XlsxServiceDep,
    current_user: CurrentUserDep,
):
    return ExportService(
        kp_repository,
        storage_service,
        pdf_service,
        csv_service,
        xlsx_service,
        current_user,
    )


ExportServiceDep = Annotated[ExportService, Depends(get_export_service)]


async def get_booklet_service(
    company_repository: CompanyRepositoryDep,
    kp_repository: KpRepositoryDep,
    storage_service: StorageServiceDep,
    pdf_service: PdfServiceDep,
    current_user: CurrentUserDep,
):
    return BookletService(
        company_repository, kp_repository, storage_service, pdf_service, current_user
    )


BookletServiceDep = Annotated[BookletService, Depends(get_booklet_service)]


def get_event_banner_service(
    kp_repository: KpRepositoryDep,
    storage_service: StorageServiceDep,
    current_user: CurrentUserDep,
) -> EventBannerService:
    return EventBannerService(kp_repository, storage_service, current_user)


EventBannerServiceDep = Annotated[EventBannerService, Depends(get_event_banner_service)]


def get_mail_campaign_session_factory() -> SessionFactory:
    return SessionLocal


MailCampaignSessionFactoryDep = Annotated[
    SessionFactory, Depends(get_mail_campaign_session_factory)
]


async def get_mail_campaign_service(
    repository: MailCampaignRepositoryDep,
    mail_service: MailServiceDep,
    current_user: CurrentUserDep,
) -> MailCampaignService:
    return MailCampaignService(repository, mail_service, current_user)


MailCampaignServiceDep = Annotated[
    MailCampaignService, Depends(get_mail_campaign_service)
]


async def get_mail_campaign_delivery(
    session_factory: MailCampaignSessionFactoryDep,
    mail_service: MailServiceDep,
) -> MailCampaignDelivery:
    return MailCampaignDelivery(
        session_factory,
        mail_service,
        pause_seconds=get_settings().MAIL_CAMPAIGN_SEND_PAUSE_SECONDS,
    )


MailCampaignDeliveryDep = Annotated[
    MailCampaignDelivery, Depends(get_mail_campaign_delivery)
]
