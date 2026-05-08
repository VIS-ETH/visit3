import { z } from "zod";

export const inviteSchema = z.object({
  email: z.email("email.valid").trim().min(1, "validation.required"),
});

export type InviteFormValues = z.infer<typeof inviteSchema>;
