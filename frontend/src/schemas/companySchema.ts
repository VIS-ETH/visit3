import { z } from "zod";

export const companySchema = z.object({
  name: z.string().trim().min(1, "validation.required"),
});
