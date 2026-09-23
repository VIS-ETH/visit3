import { z } from "zod";
import type {
  UpdateCompanyUserRequest,
  UserResponse,
} from "../../orval/generated/fastAPI.schemas";
import { zPhone } from "../../schemas/utils";

export const adminUserSchema = z.object({
  first_name: z.string().trim(),
  last_name: z.string().trim(),
  phone_number: z
    .string()
    .trim()
    .refine(
      (value) => value.length === 0 || zPhone.safeParse(value).success,
      "register.phoneNumber.invalid",
    ),
  email: z
    .email("validation.invalid_email")
    .trim()
    .min(1, "validation.required"),
  company_id: z.string(),
  user_confirmed: z.boolean(),
  is_staff: z.boolean(),
  is_admin: z.boolean(),
});

type AdminUserFormValues = z.infer<typeof adminUserSchema>;

export const emptyAdminUserFormValues: AdminUserFormValues = {
  first_name: "",
  last_name: "",
  phone_number: "",
  email: "",
  company_id: "",
  user_confirmed: false,
  is_staff: false,
  is_admin: false,
};

export const toAdminUserFormValues = (
  user: UserResponse,
): AdminUserFormValues => ({
  first_name: user.first_name ?? "",
  last_name: user.last_name ?? "",
  phone_number: user.phone_number ?? "",
  email: user.email,
  company_id: user.company_id ?? "",
  user_confirmed: user.user_confirmed,
  is_staff: user.is_staff,
  is_admin: user.is_admin,
});

export const toAdminUserRequest = (
  values: AdminUserFormValues,
  includePrivileges: boolean,
): UpdateCompanyUserRequest => ({
  first_name: values.first_name.trim() || null,
  last_name: values.last_name.trim() || null,
  phone_number: values.phone_number.trim() || null,
  email: values.email.trim(),
  company_id: values.company_id || null,
  user_confirmed: values.user_confirmed,
  ...(includePrivileges
    ? { is_staff: values.is_staff, is_admin: values.is_admin }
    : {}),
});
