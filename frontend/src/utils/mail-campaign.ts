import {
  MailCampaignSegment,
  MailCampaignStatus,
  type MailCampaignAudienceRequest,
  type MailCampaignRenderRequest,
  type MailCampaignRequest,
  type MailCampaignResponse,
} from "../orval/generated/fastAPI.schemas";
import type { MailCampaignFormValues } from "../schemas/mailCampaignSchema";

export const ZURICH_TIME_ZONE = "Europe/Zurich";

export const MAIL_CAMPAIGN_SEGMENTS: readonly MailCampaignSegment[] = [
  MailCampaignSegment.ALL,
  MailCampaignSegment.NOT_REGISTERED,
  MailCampaignSegment.REGISTERED,
  MailCampaignSegment.CONFIRMED,
  MailCampaignSegment.OFFERED,
  MailCampaignSegment.WAITLISTED,
];

const EDITABLE_STATUSES: readonly MailCampaignStatus[] = [
  MailCampaignStatus.DRAFT,
  MailCampaignStatus.SCHEDULED,
];

export function isEditableCampaign(status: MailCampaignStatus) {
  return EDITABLE_STATUSES.includes(status);
}

export const MAIL_CAMPAIGN_STATUS_COLORS: Record<MailCampaignStatus, string> = {
  DRAFT: "gray",
  SCHEDULED: "blue",
  SENDING: "yellow",
  SENT: "green",
  PARTIALLY_FAILED: "red",
};

export function emptyMailCampaignValues(
  eventId: string | null,
): MailCampaignFormValues {
  return {
    name: "",
    eventId: eventId ?? "",
    subjectDe: "",
    bodyDe: "",
    subjectEn: "",
    bodyEn: "",
    segments: [MailCampaignSegment.NOT_REGISTERED],
    boothZoneIds: [],
    includeCompanyIds: [],
    excludeCompanyIds: [],
  };
}

export function mailCampaignValues(
  campaign: MailCampaignResponse,
): MailCampaignFormValues {
  return {
    name: campaign.name,
    eventId: campaign.event_id,
    subjectDe: campaign.subject_de,
    bodyDe: campaign.body_de,
    subjectEn: campaign.subject_en,
    bodyEn: campaign.body_en,
    segments: campaign.audience.segments ?? [],
    boothZoneIds: campaign.audience.booth_zone_ids ?? [],
    includeCompanyIds: campaign.audience.include_company_ids ?? [],
    excludeCompanyIds: campaign.audience.exclude_company_ids ?? [],
  };
}

export function toMailCampaignAudienceRequest(
  values: MailCampaignFormValues,
): MailCampaignAudienceRequest {
  return {
    event_id: values.eventId,
    audience: {
      segments: values.segments,
      booth_zone_ids: values.boothZoneIds,
      include_company_ids: values.includeCompanyIds,
      exclude_company_ids: values.excludeCompanyIds,
    },
  };
}

function texts(values: MailCampaignFormValues) {
  return {
    subject_de: values.subjectDe.trim(),
    body_de: values.bodyDe,
    subject_en: values.subjectEn.trim(),
    body_en: values.bodyEn,
  };
}

export function toMailCampaignRequest(
  values: MailCampaignFormValues,
): MailCampaignRequest {
  return {
    name: values.name.trim(),
    ...texts(values),
    ...toMailCampaignAudienceRequest(values),
  };
}

export function toMailCampaignRenderRequest(
  values: MailCampaignFormValues,
  companyId: string | null,
): MailCampaignRenderRequest {
  return {
    event_id: values.eventId,
    company_id: companyId,
    ...texts(values),
  };
}

type InputPart = "year" | "month" | "day" | "hour" | "minute";

export function zurichDateTimeInput(date: Date): string {
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: ZURICH_TIME_ZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(date);
  const value = (type: InputPart) =>
    parts.find((part) => part.type === type)?.value ?? "";
  return `${value("year")}-${value("month")}-${value("day")}T${value("hour")}:${value("minute")}`;
}

const HOUR_MS = 60 * 60 * 1000;

export function nextFullHourInput(now: Date = new Date()): string {
  const nextHour = new Date(Math.floor(now.getTime() / HOUR_MS + 1) * HOUR_MS);
  return zurichDateTimeInput(nextHour);
}

export function isFutureZurichInput(value: string, now: Date = new Date()) {
  return value > zurichDateTimeInput(now);
}

export function formatZurichDateTime(
  value: string | null | undefined,
  language: string,
) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return new Intl.DateTimeFormat(language, {
    timeZone: ZURICH_TIME_ZONE,
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}
