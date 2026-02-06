import { z } from "zod";

export const resetPasswordSchema = z
  .object({
    password: z.string().min(11, "register.password.min"),
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "register.password.nomatch",
    path: ["confirmPassword"],
  });
