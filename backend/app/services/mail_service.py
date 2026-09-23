import logging
from collections.abc import Sequence
from typing import Any, cast

import grpc

from app.generated.sip.notifications import mail_pb2 as mail_pb
from app.generated.sip.notifications.mail_pb2_grpc import MailServiceStub

logger = logging.getLogger(__name__)

SENDER_FIELD_NAME_IS_A_PYTHON_KEYWORD = "from"


class MailService:
    def __init__(self, mail: MailServiceStub) -> None:
        self.mail = mail

    class Mimebody:
        class Multipart:
            def __init__(self, content_type: str, content: str) -> None:
                self.content_type = content_type
                self.content = content

        def __init__(self, multiparts: Sequence[Multipart]) -> None:
            self.parts = multiparts

    async def send_mail(self, request: mail_pb.Mail) -> None:
        try:
            logger.info("MailService sending mail via gRPC")
            await cast(Any, self.mail).SendMail(request)
            logger.info("MailService gRPC send completed")
        except grpc.RpcError as e:
            logger.error("gRPC Error")
            raise e

    def construct_mail(
        self,
        email_to: Sequence[str],
        subject: str,
        plain_text: str | None = None,
        multipart_body: Mimebody | None = None,
        email_from: str | None = None,
    ) -> mail_pb.Mail | None:
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

        if email_from:
            sender = getattr(mail, SENDER_FIELD_NAME_IS_A_PYTHON_KEYWORD)
            sender.CopyFrom(
                mail_pb.MailAddress(
                    mail_address=mail_pb.MailAddress.Address(address=email_from)
                )
            )

        if plain_text:
            mail.plain_text = plain_text
        elif multipart_body:
            for part in multipart_body.parts:
                new_part = mail.multipart_body.parts.add()
                new_part.content_type = part.content_type
                new_part.content = part.content

        return mail
