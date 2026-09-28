import { z } from "zod";

export const mailTemplateSchema = z.object({
  subjectDe: z.string().trim().min(1, "validation.required"),
  subjectEn: z.string().trim().min(1, "validation.required"),
  bodyDe: z.string().trim().min(1, "validation.required"),
  bodyEn: z.string().trim().min(1, "validation.required"),
});

export type MailTemplateFormValues = z.infer<typeof mailTemplateSchema>;

export const emptyMailTemplateValues: MailTemplateFormValues = {
  subjectDe: "",
  subjectEn: "",
  bodyDe: "",
  bodyEn: "",
};

const mailTemplateRequestSchema = mailTemplateSchema.transform((values) => ({
  subject_de: values.subjectDe,
  subject_en: values.subjectEn,
  body_de: values.bodyDe,
  body_en: values.bodyEn,
}));

export function toMailTemplateRequest(values: MailTemplateFormValues) {
  return mailTemplateRequestSchema.parse(values);
}
