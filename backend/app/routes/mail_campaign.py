from uuid import UUID

from fastapi import APIRouter, BackgroundTasks

from app.core.deps import CsrfDep, MailCampaignDeliveryDep, MailCampaignServiceDep
from app.schemas.mail import MailPreviewResponse, MailPreviewResult
from app.schemas.mail_campaign import (
    MailCampaignAudienceRequest,
    MailCampaignAudienceResponse,
    MailCampaignAudienceResult,
    MailCampaignCompanyResponse,
    MailCampaignCompanyResult,
    MailCampaignRenderRequest,
    MailCampaignRequest,
    MailCampaignResponse,
    MailCampaignResult,
    MailCampaignScheduleRequest,
    MailCampaignSummaryResponse,
    MailCampaignSummaryResult,
)

router = APIRouter(
    prefix="/mail-campaigns", tags=["mail-campaigns"], dependencies=[CsrfDep]
)


@router.get(
    "",
    operation_id="listMailCampaigns",
    response_model=list[MailCampaignSummaryResponse],
)
async def list_mail_campaigns(
    mail_campaign_service: MailCampaignServiceDep,
) -> list[MailCampaignSummaryResult]:
    return await mail_campaign_service.list_campaigns()


@router.post(
    "",
    operation_id="createMailCampaign",
    response_model=MailCampaignResponse,
)
async def create_mail_campaign(
    mail_campaign_service: MailCampaignServiceDep, request: MailCampaignRequest
) -> MailCampaignResult:
    return await mail_campaign_service.create_campaign(request)


@router.get(
    "/variables",
    operation_id="listMailCampaignVariables",
    response_model=list[str],
)
async def list_mail_campaign_variables(
    mail_campaign_service: MailCampaignServiceDep,
) -> list[str]:
    return mail_campaign_service.variables()


@router.get(
    "/companies",
    operation_id="listMailCampaignCompanies",
    response_model=list[MailCampaignCompanyResponse],
)
async def list_mail_campaign_companies(
    mail_campaign_service: MailCampaignServiceDep,
) -> list[MailCampaignCompanyResult]:
    return await mail_campaign_service.companies()


@router.post(
    "/audience",
    operation_id="previewMailCampaignAudience",
    response_model=MailCampaignAudienceResponse,
)
async def preview_mail_campaign_audience(
    mail_campaign_service: MailCampaignServiceDep,
    request: MailCampaignAudienceRequest,
) -> MailCampaignAudienceResult:
    return await mail_campaign_service.preview_audience(request)


@router.post(
    "/render",
    operation_id="renderMailCampaign",
    response_model=MailPreviewResponse,
)
async def render_mail_campaign(
    mail_campaign_service: MailCampaignServiceDep,
    request: MailCampaignRenderRequest,
) -> MailPreviewResult:
    return await mail_campaign_service.render_preview(request)


@router.post("/test-send", operation_id="testSendMailCampaign")
async def test_send_mail_campaign(
    mail_campaign_service: MailCampaignServiceDep,
    request: MailCampaignRenderRequest,
) -> None:
    await mail_campaign_service.test_send(request)


@router.get(
    "/{campaign_id}",
    operation_id="getMailCampaign",
    response_model=MailCampaignResponse,
)
async def get_mail_campaign(
    mail_campaign_service: MailCampaignServiceDep, campaign_id: UUID
) -> MailCampaignResult:
    return await mail_campaign_service.get_campaign(campaign_id)


@router.put(
    "/{campaign_id}",
    operation_id="updateMailCampaign",
    response_model=MailCampaignResponse,
)
async def update_mail_campaign(
    mail_campaign_service: MailCampaignServiceDep,
    campaign_id: UUID,
    request: MailCampaignRequest,
) -> MailCampaignResult:
    return await mail_campaign_service.update_campaign(campaign_id, request)


@router.delete("/{campaign_id}", operation_id="deleteMailCampaign")
async def delete_mail_campaign(
    mail_campaign_service: MailCampaignServiceDep, campaign_id: UUID
) -> None:
    await mail_campaign_service.delete_campaign(campaign_id)


@router.post(
    "/{campaign_id}/duplicate",
    operation_id="duplicateMailCampaign",
    response_model=MailCampaignResponse,
)
async def duplicate_mail_campaign(
    mail_campaign_service: MailCampaignServiceDep, campaign_id: UUID
) -> MailCampaignResult:
    return await mail_campaign_service.duplicate_campaign(campaign_id)


@router.post(
    "/{campaign_id}/send",
    operation_id="sendMailCampaign",
    response_model=MailCampaignResponse,
)
async def send_mail_campaign(
    mail_campaign_service: MailCampaignServiceDep,
    delivery: MailCampaignDeliveryDep,
    background_tasks: BackgroundTasks,
    campaign_id: UUID,
) -> MailCampaignResult:
    result = await mail_campaign_service.send_now(campaign_id)
    background_tasks.add_task(delivery.deliver_safely, campaign_id)
    return result


@router.post(
    "/{campaign_id}/schedule",
    operation_id="scheduleMailCampaign",
    response_model=MailCampaignResponse,
)
async def schedule_mail_campaign(
    mail_campaign_service: MailCampaignServiceDep,
    campaign_id: UUID,
    request: MailCampaignScheduleRequest,
) -> MailCampaignResult:
    return await mail_campaign_service.schedule(campaign_id, request)


@router.post(
    "/{campaign_id}/unschedule",
    operation_id="unscheduleMailCampaign",
    response_model=MailCampaignResponse,
)
async def unschedule_mail_campaign(
    mail_campaign_service: MailCampaignServiceDep, campaign_id: UUID
) -> MailCampaignResult:
    return await mail_campaign_service.unschedule(campaign_id)


@router.post(
    "/{campaign_id}/retry",
    operation_id="retryMailCampaign",
    response_model=MailCampaignResponse,
)
async def retry_mail_campaign(
    mail_campaign_service: MailCampaignServiceDep,
    delivery: MailCampaignDeliveryDep,
    background_tasks: BackgroundTasks,
    campaign_id: UUID,
) -> MailCampaignResult:
    result = await mail_campaign_service.retry(campaign_id)
    background_tasks.add_task(delivery.deliver_safely, campaign_id)
    return result
