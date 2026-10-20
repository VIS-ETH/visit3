import { z } from "zod";
import { zPhone } from "./utils";

export const profileSchema = z
  .object({
    firstName: z.string().optional(),
    lastName: z.string().optional(),
    phoneNumber: z.string().optional(),
  })
  .refine(
    (data) =>
      !data.phoneNumber?.trim() || zPhone.safeParse(data.phoneNumber).success,
    {
      message: "register.phoneNumber.invalid",
      path: ["phoneNumber"],
    },
  );

export type ProfileFormValues = z.infer<typeof profileSchema>;

export const emailChangeSchema = z.object({
  email: z
    .email("validation.invalid_email")
    .trim()
    .min(1, "validation.required"),
  currentPassword: z.string(),
});
