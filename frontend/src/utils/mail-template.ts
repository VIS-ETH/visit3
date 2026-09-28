import { isAxiosError } from "axios";
import type { MailTemplateResponse } from "../orval/generated/fastAPI.schemas";
import type { MailTemplateFormValues } from "../schemas/mailTemplateSchema";

const MAIL_TEMPLATE_INVALID_CODE = "error.mail_template_invalid";

const FORM_FIELD_BY_API_FIELD = {
  subject_de: "subjectDe",
  subject_en: "subjectEn",
  body_de: "bodyDe",
  body_en: "bodyEn",
} as const;

type MailTemplateApiField = keyof typeof FORM_FIELD_BY_API_FIELD;
export type MailTemplateField = keyof MailTemplateFormValues;
export type MailTemplateLanguage = "de" | "en";

export const MAIL_TEMPLATE_LANGUAGES: readonly MailTemplateLanguage[] = [
  "de",
  "en",
];

const FIELDS_BY_LANGUAGE: Record<
  MailTemplateLanguage,
  { subject: MailTemplateField; body: MailTemplateField }
> = {
  de: { subject: "subjectDe", body: "bodyDe" },
  en: { subject: "subjectEn", body: "bodyEn" },
};

export function mailTemplateFields(language: MailTemplateLanguage) {
  return FIELDS_BY_LANGUAGE[language];
}

export function mailTemplateLanguageOf(
  field: MailTemplateField,
): MailTemplateLanguage {
  return field === "subjectEn" || field === "bodyEn" ? "en" : "de";
}

export function mailTemplateDefaults(
  template: MailTemplateResponse,
  language: MailTemplateLanguage,
) {
  return language === "en"
    ? { subject: template.default_subject_en, body: template.default_body_en }
    : { subject: template.default_subject_de, body: template.default_body_de };
}

export function mailTemplateValues(
  template: MailTemplateResponse,
): MailTemplateFormValues {
  return {
    subjectDe: template.subject_de,
    subjectEn: template.subject_en,
    bodyDe: template.body_de,
    bodyEn: template.body_en,
  };
}

export function mailVariableSnippet(variable: string) {
  return `{{ ${variable} }}`;
}

export function insertIntoSelection(
  value: string,
  snippet: string,
  start: number,
  end: number,
) {
  return `${value.slice(0, start)}${snippet}${value.slice(end)}`;
}

interface InvalidMailTemplateField {
  field: MailTemplateField;
  variable?: string;
}

function isApiField(value: unknown): value is MailTemplateApiField {
  return typeof value === "string" && value in FORM_FIELD_BY_API_FIELD;
}

export function getInvalidMailTemplateField(
  error: unknown,
): InvalidMailTemplateField | undefined {
  if (!isAxiosError(error)) return undefined;

  const data: unknown = error.response?.data;
  if (typeof data !== "object" || data === null) return undefined;

  const { code, details } = data as { code?: unknown; details?: unknown };
  if (code !== MAIL_TEMPLATE_INVALID_CODE) return undefined;
  if (typeof details !== "object" || details === null) return undefined;

  const { field, variable } = details as {
    field?: unknown;
    variable?: unknown;
  };
  if (!isApiField(field)) return undefined;

  return {
    field: FORM_FIELD_BY_API_FIELD[field],
    variable: typeof variable === "string" ? variable : undefined,
  };
}
