import { z } from "zod";
import { zPhone } from "./utils";

export const registerSchema = z
  .object({
    email: z.string().trim().min(1, "register.required"),
    password: z.string().min(1, "register.required").min(11, "password.min"),
    confirmPassword: z.string().min(1, "register.required"),
    firstName: z.string().trim().min(1, "register.required"),
    lastName: z.string().trim().min(1, "register.required"),
    phoneNumber: z.string().optional(),
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
    path: ["companyId"],
  })
  .refine((data) => !data.phoneNumber?.trim() || zPhone.safeParse(data.phoneNumber).success, {
    message: "register.phoneNumber.invalid",
    path: ["phoneNumber"],
  });