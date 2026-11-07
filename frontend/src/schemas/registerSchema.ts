import { z } from "zod";
import { zEmail, zPhone } from "./utils";

export const registerSchema = z
  .object({
    email: zEmail("email.valid"),
    password: z.string().min(1, "validation.required").min(8, "password.min"),
    confirmPassword: z.string().min(1, "validation.required"),
    firstName: z.string().trim().min(1, "validation.required"),
    lastName: z.string().trim().min(1, "validation.required"),
    phoneNumber: z.string().optional(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "register.password.nomatch",
    path: ["confirmPassword"],
  })
  .refine(
    (data) =>
      !data.phoneNumber?.trim() || zPhone.safeParse(data.phoneNumber).success,
    {
      message: "register.phoneNumber.invalid",
      path: ["phoneNumber"],
    },
  );
