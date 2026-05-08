import { z } from "zod";
import { zPhone } from "./utils";

export const registerSchema = z
  .object({
    email: z.email("email.valid").trim().min(1, "validation.required"),
    password: z.string().min(1, "validation.required").min(11, "password.min"),
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

export type RegisterFormValues = z.infer<typeof registerSchema>;
