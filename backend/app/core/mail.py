from typing import List, Optional
from app.generated.sip.notifications import mail_pb2 as mail_pb


class Mimebody:
    class Multipart:
        def __init__(self, content_type: str, content: str):
            self.content_type = content_type
            self.content = content

    def __init__(self, multiparts: List[Multipart]):
        self.parts = multiparts


def construct_mail(
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
            mail_pb.MailAddress(mail_address=mail_pb.MailAddress.Address(address=elem))
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