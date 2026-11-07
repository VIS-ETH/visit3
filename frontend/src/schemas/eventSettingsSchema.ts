import { z } from "zod";
import type {
  KpResponse,
  KpStaffResponse,
} from "../orval/generated/fastAPI.schemas";
import { formatKpIsoDateInput } from "../utils/kp-utils";
import { isOptionalHttpUrl } from "../utils/optional-inputs";
import { kpSchema, toKpRequest } from "./kpSchema";
import { zEmail } from "./utils";

const DEFAULT_VAT_RATE_PERCENT = 8.1;
const DEFAULT_FINALIZATION_REMINDER_DAYS = 3;
export const MAX_VAT_RATE_PERCENT = 100;
const VAT_RATE_DECIMALS = 1;

const isSingleDecimal = (value: number) =>
  Number(value.toFixed(VAT_RATE_DECIMALS)) === value;

const emptyToNull = (value: string) => (value === "" ? null : value);

export const eventSettingsSchema = z.object({
  vatRatePercent: z
    .number()
    .min(0, "event_settings.vat_rate_range")
    .max(MAX_VAT_RATE_PERCENT, "event_settings.vat_rate_range")
    .refine(isSingleDecimal, "event_settings.vat_rate_decimals"),
  termsUrl: z
    .string()
    .trim()
    .refine(isOptionalHttpUrl, "validation.invalid_url"),
  notificationEmail: z.union([z.string().trim().max(0), zEmail()], {
    error: "validation.invalid_email",
  }),
  finalizationReminderDays: z
    .number()
    .int("event_settings.reminder_days_invalid")
    .min(0, "event_settings.reminder_days_invalid"),
});

export type EventSettingsFormValues = z.infer<typeof eventSettingsSchema>;

const eventSettingsRequestSchema = eventSettingsSchema.transform((values) => ({
  vat_rate_percent: values.vatRatePercent,
  terms_url: emptyToNull(values.termsUrl),
  notification_email: emptyToNull(values.notificationEmail),
  finalization_reminder_days: values.finalizationReminderDays,
}));

export const kpWithSettingsSchema = kpSchema.and(eventSettingsSchema);

export type KpWithSettingsFormValues = z.infer<typeof kpWithSettingsSchema>;

export const emptyEventSettingsValues: EventSettingsFormValues = {
  vatRatePercent: DEFAULT_VAT_RATE_PERCENT,
  termsUrl: "",
  notificationEmail: "",
  finalizationReminderDays: DEFAULT_FINALIZATION_REMINDER_DAYS,
};

export const emptyKpFormValues: KpWithSettingsFormValues = {
  name: "",
  registrationOpen: "",
  registrationEnd: "",
  finalizationDeadline: "",
  nametagsDeadline: "",
  eventDate: "",
  ...emptyEventSettingsValues,
};

export const kpFormValuesFromEvent = (
  event: KpResponse,
  settings?: Pick<KpStaffResponse, "notification_email">,
): KpWithSettingsFormValues => ({
  name: event.name,
  registrationOpen: formatKpIsoDateInput(event.registration_open),
  registrationEnd: formatKpIsoDateInput(event.registration_end),
  finalizationDeadline: formatKpIsoDateInput(event.finalization_deadline),
  nametagsDeadline: formatKpIsoDateInput(event.nametags_deadline),
  eventDate: formatKpIsoDateInput(event.event_date),
  vatRatePercent: event.vat_rate_percent,
  termsUrl: event.terms_url ?? "",
  notificationEmail: settings?.notification_email ?? "",
  finalizationReminderDays: event.finalization_reminder_days,
});

export function toKpWithSettingsRequest(values: KpWithSettingsFormValues) {
  return {
    ...toKpRequest(values),
    ...eventSettingsRequestSchema.parse(values),
  };
}
