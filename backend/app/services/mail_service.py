import logging
from collections.abc import Sequence
from email.header import Header
from typing import Any, cast

import grpc

from app.core.config import get_settings
from app.generated.sip.notifications import mail_pb2 as mail_pb
from app.generated.sip.notifications.mail_pb2_grpc import MailServiceStub

logger = logging.getLogger(__name__)

SENDER_FIELD_NAME_IS_A_PYTHON_KEYWORD = "from"
SENDER_NAME = "VISIT MAIL SERVICE"


def encode_header_text(text: str) -> str:
    if text.isascii():
        return text
    return Header(text, "utf-8").encode()


class MailDeliveryFailed(RuntimeError):
    pass


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
            # Do not propagate remote error details that might echo credentials.
            code = e.code() if isinstance(e, grpc.aio.AioRpcError) else None
            raise MailDeliveryFailed(
                f"notification API SendMail failed ({code})"
            ) from None
        except Exception as e:
            raise MailDeliveryFailed(
                f"notification API SendMail failed ({e.__class__.__name__})"
            ) from None

    def construct_mail(
        self,
        email_to: Sequence[str],
        subject: str,
        plain_text: str | None = None,
        multipart_body: Mimebody | None = None,
        email_from: str | None = None,
        sender_name: str = SENDER_NAME,
    ) -> mail_pb.Mail | None:
        if (not plain_text and not multipart_body) or not email_to:
            return None

        mail = mail_pb.Mail()
        mail.subject = encode_header_text(subject)
        mail.to.extend(
            [
                mail_pb.MailAddress(
                    mail_address=mail_pb.MailAddress.Address(address=elem)
                )
                for elem in email_to
            ]
        )

        sender_address = email_from or str(get_settings().NOTIFICATION_SENDER_EMAIL)
        sender = getattr(mail, SENDER_FIELD_NAME_IS_A_PYTHON_KEYWORD)
        sender.CopyFrom(
            mail_pb.MailAddress(
                mail_address=mail_pb.MailAddress.Address(
                    name=sender_name, address=sender_address
                )
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
