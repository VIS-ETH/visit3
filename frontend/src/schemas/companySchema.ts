import { z } from "zod";

export const companySchema = z.object({
  name: z.string().min(1, "Company name is required"),
});

export type CompanyFormData = z.infer<typeof companySchema>;
