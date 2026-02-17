import { z } from "zod";

export const registerSchema = z
  .object({
    email: z.string(),
    password: z.string().min(11, "password.min"),
    confirmPassword: z.string(),
    firstName: z.string(),
    lastName: z.string(),
    companyId: z.string().optional(),
    companyName: z.string().optional(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "register.password.nomatch",
    path: ["confirmPassword"],
  })
  .refine((data) => z.email().safeParse(data.email).success, {
    message: "email.valid",
    path: ["email"],
  })
  .refine((data) => Boolean(data.companyId?.trim()) || Boolean(data.companyName?.trim()), {
    message: "register.company.required",
    path: ["companyName"],
  });
