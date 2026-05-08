import { z } from "zod";

export const loginSchema = z.object({
  username: z.email("email.valid").trim().min(1, "register.required"),
  password: z.string().min(11, "password.min"),
});

export type LoginFormValues = z.infer<typeof loginSchema>;
