import { z } from "zod";

export const setupCompanySchema = z.object({
  name: z.string().trim().min(1, "register.required"),
});

export type SetupCompanyFormValues = z.infer<typeof setupCompanySchema>;
