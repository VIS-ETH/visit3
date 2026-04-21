import logging
from typing import List, Optional

import grpc

from app.core.config import get_settings
from app.generated.sip.notifications import mail_pb2 as mail_pb
from app.generated.sip.notifications.mail_pb2_grpc import MailServiceStub

logger = logging.getLogger(__name__)


class MailService:
    def __init__(self, mail: MailServiceStub):
        self.mail = mail

    class Mimebody:
        class Multipart:
            def __init__(self, content_type: str, content: str):
                self.content_type = content_type
                self.content = content

        def __init__(self, multiparts: List[Multipart]):
            self.parts = multiparts

    async def send_mail(self, request):
        try:
            logger.info("MailService sending mail via gRPC")
            await self.mail.SendMail(request)
            logger.info("MailService gRPC send completed")
            return None
        except grpc.RpcError as e:
            logger.error(f"gRPC Error: {e.code()} - {e.details()}")
            raise e

    def construct_mail(
        self,
        email_to: List[str],
        subject: str,
        plain_text: Optional[str] = None,
        multipart_body: Optional[Mimebody] = None,
        email_from: Optional[str] = None,
    ):
        if (not plain_text and not multipart_body) or not email_to:
            return None

        mail = mail_pb.Mail()
        mail.subject = subject
        mail.to.extend(
            [
                mail_pb.MailAddress(
                    mail_address=mail_pb.MailAddress.Address(address=elem)
                )
                for elem in email_to
            ]
        )

        # Since from is a keyword in python we do this workaround
        if email_from:
            temp_address = mail_pb.MailAddress(
                mail_address=mail_pb.MailAddress.Address(address=email_from)
            )
            getattr(mail, "from").CopyFrom(temp_address)

        if plain_text:
            mail.plain_text = plain_text
        else:
            for part in multipart_body.parts:
                new_part = mail.multipart_body.parts.add()
                new_part.content_type = part.content_type
                new_part.content = part.content

        return mail

    async def send_forget_password_mail(self, email: str, token: str):
        logger.info(f"Preparing forget-password mail for: {email}")
        request = self.construct_mail(
            [email],
            "VISIT Reset Password",
            plain_text=f"Go to this link to reset your password {get_settings().VISIT_FRONTEND_SERVER_URL}/reset/{token}",
        )
        await self.send_mail(request)

    async def send_confirm_email_mail(self, email: str, token: str):
        logger.info(f"Preparing confirm-email mail for: {email}")
        request = self.construct_mail(
            [email],
            "Confirm Your Account For VISIT",
            plain_text=f"Go to this link to confirm your account: {get_settings().VISIT_FRONTEND_SERVER_URL}/confirm-email/{token}",
        )
        await self.send_mail(request)

    async def send_company_invite_mail(self, email: str, company_name: str, token: str):
        logger.info(f"Preparing company invite mail for: {email}")
        request = self.construct_mail(
            [email],
            f"You've been invited to join {company_name} on VISIT",
            plain_text=(
                f"You've been invited to join {company_name} on VISIT.\n\n"
                f"Click this link to accept: {get_settings().VISIT_FRONTEND_SERVER_URL}/company/join/{token}"
            ),
        )
        await self.send_mail(request)
