import type { UseFormReturnType } from "@mantine/form";
import type { CompanyProfileFormValues } from "../../schemas/companyProfileSchema";

export interface CompanyProfileFieldsProps {
  form: UseFormReturnType<CompanyProfileFormValues>;
  disabled: boolean;
}

export const MANDATORY_PROFILE_FIELDS = [
  "description",
  "kp_contact_user_id",
  "billing_company_name",
  "billing_street",
  "billing_postal_code",
  "billing_city",
  "billing_country",
  "billing_email",
] as const;

type MandatoryProfileField = (typeof MANDATORY_PROFILE_FIELDS)[number];

export const profileFieldId = (field: string) =>
  `company-profile-${field.replaceAll("_", "-")}`;

const MANDATORY_FIELD_LABEL_KEYS: Record<MandatoryProfileField, string> = {
  description: "company_profile_form.description",
  kp_contact_user_id: "company_profile_form.kp_contact_user",
  billing_company_name: "company_profile_form.billing_company_name",
  billing_street: "company_profile_form.billing_street",
  billing_postal_code: "company_profile_form.billing_postal_code",
  billing_city: "company_profile_form.billing_city",
  billing_country: "company_profile_form.billing_country",
  billing_email: "company_profile_form.billing_email",
};

const isMandatoryProfileField = (
  field: string,
): field is MandatoryProfileField =>
  MANDATORY_PROFILE_FIELDS.some((candidate) => candidate === field);

export const mandatoryFieldLabelKey = (field: string) =>
  isMandatoryProfileField(field) ? MANDATORY_FIELD_LABEL_KEYS[field] : field;
