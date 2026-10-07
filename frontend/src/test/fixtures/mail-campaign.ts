import type {
  BoothZoneResponse,
  KpResponse,
  MailCampaignAudienceResponse,
  MailCampaignCompanyResponse,
  MailCampaignResponse,
  MailPreviewResponse,
} from "../../orval/generated/fastAPI.schemas";

export const testCampaignEvent: KpResponse = {
  id: "event-1",
  name: "Kontaktparty 2030",
  registration_open: "2030-05-01",
  registration_end: "2030-06-01",
  finalization_deadline: "2030-06-15",
  nametags_deadline: "2030-06-20",
  event_date: "2030-07-10",
  vat_rate_percent: 8.1,
  terms_url: null,
  finalization_reminder_days: 3,
  max_nametags_per_booking: 10,
};

export const testCampaignZone: BoothZoneResponse = {
  id: "zone-1",
  event_id: testCampaignEvent.id,
  name: "Main hall",
  description: "",
  color: "#112233",
  order: 1,
  booth_size: 4,
  base_price: 100000,
  registration_open: true,
  included_services: [],
};

export const testCampaignCompanies: MailCampaignCompanyResponse[] = [
  { id: "company-acme", name: "Acme AG" },
  { id: "company-beta", name: "Beta GmbH" },
  { id: "company-silent", name: "Silent AG" },
];

export const testCampaignAudience: MailCampaignAudienceResponse = {
  recipient_count: 2,
  skipped_count: 1,
  recipients: [
    {
      company_id: "company-acme",
      company_name: "Acme AG",
      email: "ada@acme.example",
      source: "CONTACT",
      skip_reason: null,
      manually_included: false,
    },
    {
      company_id: "company-beta",
      company_name: "Beta GmbH",
      email: "info@beta.example",
      source: "GENERAL_EMAIL",
      skip_reason: null,
      manually_included: false,
    },
    {
      company_id: "company-silent",
      company_name: "Silent AG",
      email: null,
      source: null,
      skip_reason: "NO_ADDRESS",
      manually_included: false,
    },
  ],
};

export const testCampaignPreview: MailPreviewResponse = {
  subject: "Erinnerung / Reminder",
  html: "<p>Hallo Ada</p>",
  text: "Hallo Ada",
};

export const testDraftCampaign: MailCampaignResponse = {
  id: "campaign-1",
  name: "Registration reminder",
  event_id: testCampaignEvent.id,
  event_name: testCampaignEvent.name,
  status: "DRAFT",
  scheduled_at: null,
  started_at: null,
  finished_at: null,
  created_at: "2030-05-02T08:00:00Z",
  updated_at: "2030-05-02T08:00:00Z",
  counts: { pending: 0, sent: 0, failed: 0, skipped: 0 },
  subject_de: "Erinnerung",
  subject_en: "Reminder",
  body_de: "<p>Hallo {{ name }}</p>",
  body_en: "<p>Hello {{ name }}</p>",
  audience: {
    segments: ["NOT_REGISTERED"],
    booth_zone_ids: [],
    include_company_ids: [],
    exclude_company_ids: [],
  },
  recipients: [],
};

export const testFailedCampaign: MailCampaignResponse = {
  ...testDraftCampaign,
  id: "campaign-2",
  name: "Last call",
  status: "PARTIALLY_FAILED",
  started_at: "2030-05-03T08:00:00Z",
  finished_at: "2030-05-03T08:01:00Z",
  counts: { pending: 0, sent: 1, failed: 1, skipped: 1 },
  recipients: [
    {
      id: "recipient-1",
      company_id: "company-acme",
      company_name: "Acme AG",
      email: "ada@acme.example",
      source: "CONTACT",
      status: "SENT",
      skip_reason: null,
      error: null,
      attempts: 1,
      last_attempt_at: "2030-05-03T08:00:10Z",
      sent_at: "2030-05-03T08:00:10Z",
    },
    {
      id: "recipient-2",
      company_id: "company-beta",
      company_name: "Beta GmbH",
      email: "info@beta.example",
      source: "GENERAL_EMAIL",
      status: "FAILED",
      skip_reason: null,
      error: "DELIVERY_FAILED",
      attempts: 1,
      last_attempt_at: "2030-05-03T08:00:20Z",
      sent_at: null,
    },
    {
      id: "recipient-3",
      company_id: "company-silent",
      company_name: "Silent AG",
      email: null,
      source: null,
      status: "SKIPPED",
      skip_reason: "NO_ADDRESS",
      error: null,
      attempts: 0,
      last_attempt_at: null,
      sent_at: null,
    },
  ],
};
