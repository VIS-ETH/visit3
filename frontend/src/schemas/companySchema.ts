import { z } from "zod";

export const companySchema = z.object({
  name: z.string().min(1, "validation.required"),
});

export type CompanyFormValues = z.infer<typeof companySchema>;
