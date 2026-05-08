import { z } from "zod";

export const forgetPasswordSchema = z.object({
  email: z.email("email.valid").trim().min(1, "validation.required"),
});

export type ForgetPasswordFormValues = z.infer<typeof forgetPasswordSchema>;
