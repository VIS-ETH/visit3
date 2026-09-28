from fastapi import APIRouter

from app.core.deps import CsrfDep, MailTemplateAdminServiceDep
from app.schemas.mail import (
    MailPreviewResponse,
    MailPreviewResult,
    MailTemplateResponse,
    MailTemplateResult,
    UpdateMailTemplateRequest,
)

router = APIRouter(prefix="/mail-templates", tags=["mail"], dependencies=[CsrfDep])


@router.get(
    "",
    operation_id="listMailTemplates",
    response_model=list[MailTemplateResponse],
)
async def list_mail_templates(
    mail_template_admin_service: MailTemplateAdminServiceDep,
) -> list[MailTemplateResult]:
    return await mail_template_admin_service.list_templates()


@router.get(
    "/{key}",
    operation_id="getMailTemplate",
    response_model=MailTemplateResponse,
)
async def get_mail_template(
    mail_template_admin_service: MailTemplateAdminServiceDep, key: str
) -> MailTemplateResult:
    return await mail_template_admin_service.get_template(key)


@router.put(
    "/{key}",
    operation_id="updateMailTemplate",
    response_model=MailTemplateResponse,
)
async def update_mail_template(
    mail_template_admin_service: MailTemplateAdminServiceDep,
    key: str,
    request: UpdateMailTemplateRequest,
) -> MailTemplateResult:
    return await mail_template_admin_service.update_template(key, request)


@router.delete(
    "/{key}",
    operation_id="resetMailTemplate",
    response_model=MailTemplateResponse,
)
async def reset_mail_template(
    mail_template_admin_service: MailTemplateAdminServiceDep, key: str
) -> MailTemplateResult:
    return await mail_template_admin_service.reset_template(key)


@router.post(
    "/{key}/preview",
    operation_id="previewMailTemplate",
    response_model=MailPreviewResponse,
)
async def preview_mail_template(
    mail_template_admin_service: MailTemplateAdminServiceDep, key: str
) -> MailPreviewResult:
    return await mail_template_admin_service.preview(key)


@router.post("/{key}/test-send", operation_id="testSendMailTemplate")
async def test_send_mail_template(
    mail_template_admin_service: MailTemplateAdminServiceDep, key: str
) -> None:
    await mail_template_admin_service.test_send(key)
