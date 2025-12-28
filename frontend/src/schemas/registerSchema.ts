import { z } from "zod";

export const registerSchema = z
  .object({
    email: z.string(),
    password: z.string().min(11, "register.password.min"),
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "register.password.nomatch",
    path: ["confirmPassword"],
  })
  .refine((data) => z.email().safeParse(data.email).success, {
    message: "register.email.valid",
    path: ["email"],
  });