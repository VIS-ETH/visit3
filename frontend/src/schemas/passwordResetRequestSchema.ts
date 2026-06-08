import { z } from "zod";

export const passwordResetRequestSchema = z.object({
  email: z.email("email.valid").trim().min(1, "validation.required"),
});

export type PasswordResetRequestFormValues = z.infer<
  typeof passwordResetRequestSchema
>;
