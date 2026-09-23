import {
  MultiSelect,
  NumberInput,
  SimpleGrid,
  Stack,
  TextInput,
  Textarea,
} from "@mantine/core";
import { useTranslation } from "react-i18next";
import { KpCompanyLanguage } from "../../orval/generated/fastAPI.schemas";
import type { IndustryResponse } from "../../orval/generated/fastAPI.schemas";
import { PROFILE_DESCRIPTION_MAX_LENGTH } from "../../schemas/companyProfileSchema";
import {
  profileFieldId,
  type CompanyProfileFieldsProps,
} from "./company-profile-fields";

interface CompanyDetailsFieldsProps extends CompanyProfileFieldsProps {
  industries: IndustryResponse[];
}

const CompanyDetailsFields = ({
  form,
  disabled,
  industries,
}: CompanyDetailsFieldsProps) => {
  const { t } = useTranslation();

  const languageOptions = [
    {
      value: KpCompanyLanguage.GERMAN,
      label: t("company_profile_form.language_german"),
    },
    {
      value: KpCompanyLanguage.ENGLISH,
      label: t("company_profile_form.language_english"),
    },
    {
      value: KpCompanyLanguage.FRENCH,
      label: t("company_profile_form.language_french"),
    },
    {
      value: KpCompanyLanguage.ITALIAN,
      label: t("company_profile_form.language_italian"),
    },
  ];

  return (
    <Stack gap="md">
      <TextInput
        id={profileFieldId("brand_name")}
        label={t("company_profile_form.brand_name")}
        disabled={disabled}
        {...form.getInputProps("brand_name")}
      />
      <Textarea
        id={profileFieldId("description")}
        label={t("company_profile_form.description")}
        description={t("company_profile_form.description_counter", {
          current: form.values.description.length,
          max: PROFILE_DESCRIPTION_MAX_LENGTH,
        })}
        withAsterisk
        autosize
        minRows={4}
        maxRows={10}
        maxLength={PROFILE_DESCRIPTION_MAX_LENGTH}
        disabled={disabled}
        {...form.getInputProps("description")}
      />
      <TextInput
        id={profileFieldId("website")}
        label={t("company_profile_form.website")}
        placeholder={t("company_profile_form.website_placeholder")}
        disabled={disabled}
        {...form.getInputProps("website")}
      />
      <MultiSelect
        id={profileFieldId("industry_ids")}
        label={t("company_profile_form.industries")}
        placeholder={t("company_profile_form.industries_placeholder")}
        data={industries.map((industry) => ({
          value: industry.id,
          label: industry.name,
        }))}
        searchable
        clearable
        disabled={disabled}
        {...form.getInputProps("industry_ids")}
      />
      <MultiSelect
        id={profileFieldId("languages")}
        label={t("company_profile_form.languages")}
        placeholder={t("company_profile_form.languages_placeholder")}
        data={languageOptions}
        clearable
        disabled={disabled}
        {...form.getInputProps("languages")}
      />
      <TextInput
        id={profileFieldId("places_of_work")}
        label={t("company_profile_form.places_of_work")}
        placeholder={t("company_profile_form.places_of_work_placeholder")}
        disabled={disabled}
        {...form.getInputProps("places_of_work")}
      />
      <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
        <NumberInput
          id={profileFieldId("employee_count_switzerland")}
          label={t("company_profile_form.employee_count_switzerland")}
          min={0}
          allowNegative={false}
          allowDecimal={false}
          disabled={disabled}
          {...form.getInputProps("employee_count_switzerland")}
        />
        <NumberInput
          id={profileFieldId("employee_count_worldwide")}
          label={t("company_profile_form.employee_count_worldwide")}
          min={0}
          allowNegative={false}
          allowDecimal={false}
          disabled={disabled}
          {...form.getInputProps("employee_count_worldwide")}
        />
      </SimpleGrid>
    </Stack>
  );
};

export default CompanyDetailsFields;
