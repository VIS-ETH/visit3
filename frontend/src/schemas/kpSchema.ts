import { z } from "zod";

const DATE_INPUT_PATTERN = /^(\d{2})\.(\d{2})\.(\d{4})$/;

function buildUtcDate(day: number, month: number, year: number) {
  return new Date(Date.UTC(year, month - 1, day));
}

export function parseKpDateInput(value: string): Date | null {
  const match = DATE_INPUT_PATTERN.exec(value.trim());
  if (!match) {
    return null;
  }

  const [, dayString, monthString, yearString] = match;
  const day = Number(dayString);
  const month = Number(monthString);
  const year = Number(yearString);
  const date = buildUtcDate(day, month, year);

  if (
    date.getUTCFullYear() !== year ||
    date.getUTCMonth() !== month - 1 ||
    date.getUTCDate() !== day
  ) {
    return null;
  }

  return date;
}

export function formatKpDateInput(date: Date) {
  const day = String(date.getDate()).padStart(2, "0");
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const year = date.getFullYear();
  return `${day}.${month}.${year}`;
}

export function formatKpDisplayDate(dateString?: string) {
  if (!dateString) return "-";

  const [yearString, monthString, dayString] = dateString.split("-");
  const year = Number(yearString);
  const month = Number(monthString);
  const day = Number(dayString);

  if (!year || !month || !day) return "-";

  return `${String(day).padStart(2, "0")}.${String(month).padStart(2, "0")}.${year}`;
}

export function toKpIsoDate(value: string) {
  const parsed = parseKpDateInput(value);
  if (!parsed) {
    throw new Error(`Invalid KP date input: ${value}`);
  }

  return parsed.toISOString().slice(0, 10);
}

export const kpSchema = z
  .object({
    name: z.string().trim().min(1, "kp.dashboard.invalid_name"),
    registrationOpen: z
      .string()
      .trim()
      .min(1, "register.required")
      .refine(
        (value) => parseKpDateInput(value) !== null,
        "kp.dashboard.invalid_date",
      ),
    registrationEnd: z
      .string()
      .trim()
      .min(1, "register.required")
      .refine(
        (value) => parseKpDateInput(value) !== null,
        "kp.dashboard.invalid_date",
      ),
    finalizationDeadline: z
      .string()
      .trim()
      .min(1, "register.required")
      .refine(
        (value) => parseKpDateInput(value) !== null,
        "kp.dashboard.invalid_date",
      ),
    eventDate: z
      .string()
      .trim()
      .min(1, "register.required")
      .refine(
        (value) => parseKpDateInput(value) !== null,
        "kp.dashboard.invalid_date",
      ),
  })
  .superRefine((values, ctx) => {
    const registrationOpen = parseKpDateInput(values.registrationOpen);
    const registrationEnd = parseKpDateInput(values.registrationEnd);
    const finalizationDeadline = parseKpDateInput(values.finalizationDeadline);
    const eventDate = parseKpDateInput(values.eventDate);

    if (
      !registrationOpen ||
      !registrationEnd ||
      !finalizationDeadline ||
      !eventDate
    ) {
      return;
    }

    if (registrationEnd <= registrationOpen) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["registrationEnd"],
        message: "kp.dashboard.registration_end_after_open",
      });
    }

    if (finalizationDeadline < registrationEnd) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["finalizationDeadline"],
        message: "kp.dashboard.finalization_deadline_after_registration_end",
      });
    }

    if (eventDate <= registrationEnd) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["eventDate"],
        message: "kp.dashboard.event_date_after_registration_end",
      });
    }

    if (finalizationDeadline >= eventDate) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["finalizationDeadline"],
        message: "kp.dashboard.finalization_deadline_before_event",
      });
    }
  });

export type KpFormValues = z.infer<typeof kpSchema>;
