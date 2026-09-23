import type {
  MailPreviewResponse,
  MailTemplateResponse,
} from "../../orval/generated/fastAPI.schemas";

export const testTemplateKey = "booking_registered";
export const testOtherTemplateKey = "password_reset";

export const testMailTemplate: MailTemplateResponse = {
  key: testTemplateKey,
  subject_de: "Buchung eingegangen",
  subject_en: "Booking received",
  body_de: "Hallo {{ company_name }}",
  body_en: "Hello {{ company_name }}",
  default_subject_de: "Buchung registriert",
  default_subject_en: "Booking registered",
  default_body_de: "Guten Tag {{ company_name }}",
  default_body_en: "Good day {{ company_name }}",
  variables: ["company_name", "event_name"],
  is_customized: true,
  updated_at: "2026-03-01T10:00:00Z",
  updated_by_user_id: "staff-1",
};

export const testDefaultMailTemplate: MailTemplateResponse = {
  ...testMailTemplate,
  subject_de: testMailTemplate.default_subject_de,
  subject_en: testMailTemplate.default_subject_en,
  body_de: testMailTemplate.default_body_de,
  body_en: testMailTemplate.default_body_en,
  is_customized: false,
  updated_at: null,
  updated_by_user_id: null,
};

export const testOtherMailTemplate: MailTemplateResponse = {
  key: testOtherTemplateKey,
  subject_de: "Passwort zurücksetzen",
  subject_en: "Reset your password",
  body_de: "Hallo {{ first_name }}",
  body_en: "Hello {{ first_name }}",
  default_subject_de: "Passwort zurücksetzen",
  default_subject_en: "Reset your password",
  default_body_de: "Hallo {{ first_name }}",
  default_body_en: "Hello {{ first_name }}",
  variables: ["first_name"],
  is_customized: false,
  updated_at: null,
  updated_by_user_id: null,
};

export const testMailPreview: MailPreviewResponse = {
  subject: "Booking received",
  html: "<p>Hello Acme AG</p>",
  text: "Hello Acme AG",
};
