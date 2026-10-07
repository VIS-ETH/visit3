import { z } from "zod";
import { MailCampaignSegment } from "../orval/generated/fastAPI.schemas";

export const mailCampaignSchema = z
  .object({
    name: z.string().trim().min(1, "validation.required"),
    eventId: z.string().min(1, "validation.required"),
    subjectDe: z.string().trim().min(1, "validation.required"),
    bodyDe: z.string().trim().min(1, "validation.required"),
    subjectEn: z.string(),
    bodyEn: z.string(),
    segments: z.array(z.enum(MailCampaignSegment)),
    boothZoneIds: z.array(z.string()),
    includeCompanyIds: z.array(z.string()),
    excludeCompanyIds: z.array(z.string()),
  })
  .superRefine((values, context) => {
    const hasSubject = values.subjectEn.trim().length > 0;
    const hasBody = values.bodyEn.trim().length > 0;
    if (hasSubject === hasBody) return;
    context.addIssue({
      code: "custom",
      message: "mail_campaigns.english_incomplete",
      path: [hasSubject ? "bodyEn" : "subjectEn"],
    });
  });

export type MailCampaignFormValues = z.infer<typeof mailCampaignSchema>;
