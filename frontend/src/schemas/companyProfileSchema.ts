import { z } from "zod";
import { KpCompanyLanguage } from "../orval/generated/fastAPI.schemas";
import type {
  CompanyProfileResponse,
  UpdateCompanyProfileRequest,
} from "../orval/generated/fastAPI.schemas";
import { zPhone } from "./utils";

export const PROFILE_DESCRIPTION_MAX_LENGTH = 2500;

const COUNTRY_CODE_PATTERN = /^[A-Z]{2}$/;

const isBlank = (value: string) => value.trim().length === 0;

const employeeCount = z.union(
  [
    z.literal(""),
    z
      .number()
      .int("validation.invalid_integer")
      .min(0, "validation.out_of_range"),
  ],
  "validation.invalid_integer",
);

export const companyProfileSchema = z.object({
  description: z
    .string()
    .trim()
    .min(1, "validation.required")
    .max(PROFILE_DESCRIPTION_MAX_LENGTH, "validation.too_long"),
  website: z
    .string()
    .trim()
    .refine(
      (value) => isBlank(value) || URL.canParse(value),
      "validation.invalid_url",
    ),
  brand_name: z.string().trim(),
  general_email: z
    .string()
    .trim()
    .refine(
      (value) => isBlank(value) || z.email().safeParse(value).success,
      "validation.invalid_email",
    ),
  general_phone: z
    .string()
    .trim()
    .refine(
      (value) => isBlank(value) || zPhone.safeParse(value).success,
      "register.phoneNumber.invalid",
    ),
  places_of_work: z.string().trim(),
  employee_count_switzerland: employeeCount,
  employee_count_worldwide: employeeCount,
  offers_internships: z.boolean(),
  offers_part_time: z.boolean(),
  offers_theses: z.boolean(),
  offers_graduate_positions: z.boolean(),
  languages: z.array(z.enum(KpCompanyLanguage)),
  industry_ids: z.array(z.string()),
  kp_contact_user_id: z.string().min(1, "validation.required"),
  billing_company_name: z.string().trim().min(1, "validation.required"),
  billing_street: z.string().trim().min(1, "validation.required"),
  billing_house_number: z.string().trim(),
  billing_postal_code: z.string().trim().min(1, "validation.required"),
  billing_city: z.string().trim().min(1, "validation.required"),
  billing_country: z
    .string()
    .trim()
    .regex(COUNTRY_CODE_PATTERN, "company_profile_form.errors.country"),
  billing_vat_number: z.string().trim(),
  billing_email: z
    .email("validation.invalid_email")
    .trim()
    .min(1, "validation.required"),
});

export type CompanyProfileFormValues = z.infer<typeof companyProfileSchema>;

export const emptyCompanyProfileFormValues: CompanyProfileFormValues = {
  description: "",
  website: "",
  brand_name: "",
  general_email: "",
  general_phone: "",
  places_of_work: "",
  employee_count_switzerland: "",
  employee_count_worldwide: "",
  offers_internships: false,
  offers_part_time: false,
  offers_theses: false,
  offers_graduate_positions: false,
  languages: [],
  industry_ids: [],
  kp_contact_user_id: "",
  billing_company_name: "",
  billing_street: "",
  billing_house_number: "",
  billing_postal_code: "",
  billing_city: "",
  billing_country: "",
  billing_vat_number: "",
  billing_email: "",
};

export const toCompanyProfileFormValues = (
  profile: CompanyProfileResponse,
): CompanyProfileFormValues => ({
  description: profile.description ?? "",
  website: profile.website ?? "",
  brand_name: profile.brand_name ?? "",
  general_email: profile.general_email ?? "",
  general_phone: profile.general_phone ?? "",
  places_of_work: profile.places_of_work ?? "",
  employee_count_switzerland: profile.employee_count_switzerland ?? "",
  employee_count_worldwide: profile.employee_count_worldwide ?? "",
  offers_internships: profile.offers_internships ?? false,
  offers_part_time: profile.offers_part_time ?? false,
  offers_theses: profile.offers_theses ?? false,
  offers_graduate_positions: profile.offers_graduate_positions ?? false,
  languages: profile.languages ?? [],
  industry_ids: (profile.industries ?? []).map((industry) => industry.id),
  kp_contact_user_id: profile.kp_contact_user_id ?? "",
  billing_company_name: profile.billing_company_name ?? "",
  billing_street: profile.billing_street ?? "",
  billing_house_number: profile.billing_house_number ?? "",
  billing_postal_code: profile.billing_postal_code ?? "",
  billing_city: profile.billing_city ?? "",
  billing_country: profile.billing_country ?? "",
  billing_vat_number: profile.billing_vat_number ?? "",
  billing_email: profile.billing_email ?? "",
});

const trimmedOrNull = (value: string) => (isBlank(value) ? null : value.trim());

const countOrNull = (value: number | "") => (value === "" ? null : value);

export const toCompanyProfileRequest = (
  values: CompanyProfileFormValues,
): UpdateCompanyProfileRequest => ({
  description: values.description.trim(),
  website: trimmedOrNull(values.website),
  brand_name: values.brand_name.trim(),
  general_email: trimmedOrNull(values.general_email),
  general_phone: trimmedOrNull(values.general_phone),
  places_of_work: values.places_of_work.trim(),
  employee_count_switzerland: countOrNull(values.employee_count_switzerland),
  employee_count_worldwide: countOrNull(values.employee_count_worldwide),
  offers_internships: values.offers_internships,
  offers_part_time: values.offers_part_time,
  offers_theses: values.offers_theses,
  offers_graduate_positions: values.offers_graduate_positions,
  languages: values.languages,
  industry_ids: values.industry_ids,
  kp_contact_user_id: trimmedOrNull(values.kp_contact_user_id),
  billing_company_name: values.billing_company_name.trim(),
  billing_street: values.billing_street.trim(),
  billing_house_number: values.billing_house_number.trim(),
  billing_postal_code: values.billing_postal_code.trim(),
  billing_city: values.billing_city.trim(),
  billing_country: values.billing_country.trim().toUpperCase(),
  billing_vat_number: trimmedOrNull(values.billing_vat_number),
  billing_email: trimmedOrNull(values.billing_email),
});

export const toBookletPageRequest = (
  values: CompanyProfileFormValues,
): UpdateCompanyProfileRequest => {
  const request = toCompanyProfileRequest(values);
  const hasValidEmail = companyProfileSchema.shape.general_email.safeParse(
    values.general_email,
  ).success;
  return {
    description: request.description,
    website: request.website,
    brand_name: request.brand_name,
    general_email: hasValidEmail ? request.general_email : null,
    general_phone: request.general_phone,
    places_of_work: request.places_of_work,
    employee_count_switzerland: request.employee_count_switzerland,
    employee_count_worldwide: request.employee_count_worldwide,
    offers_internships: request.offers_internships,
    offers_part_time: request.offers_part_time,
    offers_theses: request.offers_theses,
    offers_graduate_positions: request.offers_graduate_positions,
    languages: request.languages,
    industry_ids: request.industry_ids,
  };
};
