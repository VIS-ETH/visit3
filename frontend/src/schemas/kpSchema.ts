import { z } from "zod";
import { parseKpDateInput, toKpIsoDate } from "../utils/kp-utils";

const HEX_COLOR_PATTERN = /^#[0-9A-Fa-f]{6}$/;

export const kpSchema = z
  .object({
    name: z.string().trim().min(1, "kp.dashboard.invalid_name"),
    registrationOpen: z
      .string()
      .trim()
      .min(1, "validation.required")
      .refine(
        (value) => parseKpDateInput(value) !== null,
        "kp.dashboard.invalid_date",
      ),
    registrationEnd: z
      .string()
      .trim()
      .min(1, "validation.required")
      .refine(
        (value) => parseKpDateInput(value) !== null,
        "kp.dashboard.invalid_date",
      ),
    finalizationDeadline: z
      .string()
      .trim()
      .min(1, "validation.required")
      .refine(
        (value) => parseKpDateInput(value) !== null,
        "kp.dashboard.invalid_date",
      ),
    nametagsDeadline: z
      .string()
      .trim()
      .min(1, "validation.required")
      .refine(
        (value) => parseKpDateInput(value) !== null,
        "kp.dashboard.invalid_date",
      ),
    eventDate: z
      .string()
      .trim()
      .min(1, "validation.required")
      .refine(
        (value) => parseKpDateInput(value) !== null,
        "kp.dashboard.invalid_date",
      ),
  })
  .superRefine((values, ctx) => {
    const registrationOpen = parseKpDateInput(values.registrationOpen);
    const registrationEnd = parseKpDateInput(values.registrationEnd);
    const finalizationDeadline = parseKpDateInput(values.finalizationDeadline);
    const nametagsDeadline = parseKpDateInput(values.nametagsDeadline);
    const eventDate = parseKpDateInput(values.eventDate);

    if (
      !registrationOpen ||
      !registrationEnd ||
      !finalizationDeadline ||
      !nametagsDeadline ||
      !eventDate
    ) {
      return;
    }

    if (registrationEnd <= registrationOpen) {
      ctx.addIssue({
        code: "custom",
        path: ["registrationEnd"],
        message: "kp.dashboard.registration_end_after_open",
      });
    }

    if (finalizationDeadline < registrationEnd) {
      ctx.addIssue({
        code: "custom",
        path: ["finalizationDeadline"],
        message: "kp.dashboard.finalization_deadline_after_registration_end",
      });
    }

    if (eventDate <= registrationEnd) {
      ctx.addIssue({
        code: "custom",
        path: ["eventDate"],
        message: "kp.dashboard.event_date_after_registration_end",
      });
    }

    if (nametagsDeadline < registrationEnd) {
      ctx.addIssue({
        code: "custom",
        path: ["nametagsDeadline"],
        message: "kp.dashboard.nametags_deadline_after_registration_end",
      });
    }

    if (finalizationDeadline >= eventDate) {
      ctx.addIssue({
        code: "custom",
        path: ["finalizationDeadline"],
        message: "kp.dashboard.finalization_deadline_before_event",
      });
    }

    if (nametagsDeadline >= eventDate) {
      ctx.addIssue({
        code: "custom",
        path: ["nametagsDeadline"],
        message: "kp.dashboard.nametags_deadline_before_event",
      });
    }
  });

export type KpFormValues = z.infer<typeof kpSchema>;

export const kpRequestSchema = kpSchema.transform((values) => ({
  name: values.name.trim(),
  registration_open: toKpIsoDate(values.registrationOpen),
  registration_end: toKpIsoDate(values.registrationEnd),
  finalization_deadline: toKpIsoDate(values.finalizationDeadline),
  nametags_deadline: toKpIsoDate(values.nametagsDeadline),
  event_date: toKpIsoDate(values.eventDate),
}));

export function toKpRequest(values: KpFormValues) {
  return kpRequestSchema.parse(values);
}

export const boothZoneSchema = z.object({
  name: z.string().trim().min(1, "validation.required"),
  description: z.string(),
  color: z
    .string()
    .trim()
    .min(1, "validation.required")
    .regex(HEX_COLOR_PATTERN, "kp.manage.zone_color_invalid_hex"),
  capacity: z.number().min(0, "kp.manage.zone_number_non_negative"),
  boothSize: z.number().min(0, "kp.manage.zone_number_non_negative"),
  basePrice: z.number().min(0, "kp.manage.zone_number_non_negative"),
});

export type BoothZoneFormValues = z.infer<typeof boothZoneSchema>;

export const serviceSchema = z.object({
  name: z.string().trim().min(1, "validation.required"),
  description: z.string(),
  price: z.number().min(0, "kp.manage.service_number_non_negative"),
  maxPerBooking: z.number().min(1, "kp.manage.service_max_per_booking_min"),
  maxTotal: z.number().min(0, "kp.manage.service_number_non_negative"),
  isActive: z.boolean(),
});

export type ServiceFormValues = z.infer<typeof serviceSchema>;
