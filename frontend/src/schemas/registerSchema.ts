import { z } from "zod";

export const registerSchema = z
  .object({
    email: z.string(),
    password: z.string().min(11, "password.min"),
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "register.password.nomatch",
    path: ["confirmPassword"],
  })
  .refine((data) => z.email().safeParse(data.email).success, {
    message: "email.valid",
    path: ["email"],
  });