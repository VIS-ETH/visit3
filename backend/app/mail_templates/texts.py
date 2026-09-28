from dataclasses import dataclass


@dataclass(frozen=True)
class MailTemplateTexts:
    subject_de: str
    subject_en: str
    body_de: str
    body_en: str
