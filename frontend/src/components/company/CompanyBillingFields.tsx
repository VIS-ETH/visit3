import { SimpleGrid, Stack, TextInput } from "@mantine/core";
import { useTranslation } from "react-i18next";
import {
  profileFieldId,
  type CompanyProfileFieldsProps,
} from "./company-profile-fields";
import { useCountryOptions } from "./country-options";
import SearchSelect from "../SearchSelect";

const CompanyBillingFields = ({
  form,
  disabled,
}: CompanyProfileFieldsProps) => {
  const { t } = useTranslation();
  const countryOptions = useCountryOptions();

  return (
    <Stack gap="md">
      <TextInput
        id={profileFieldId("billing_company_name")}
        label={t("company_profile_form.billing_company_name")}
        withAsterisk
        disabled={disabled}
        {...form.getInputProps("billing_company_name")}
      />
      <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="md">
        <TextInput
          id={profileFieldId("billing_street")}
          label={t("company_profile_form.billing_street")}
          withAsterisk
          disabled={disabled}
          {...form.getInputProps("billing_street")}
        />
        <TextInput
          id={profileFieldId("billing_house_number")}
          label={t("company_profile_form.billing_house_number")}
          disabled={disabled}
          {...form.getInputProps("billing_house_number")}
        />
        <TextInput
          id={profileFieldId("billing_postal_code")}
          label={t("company_profile_form.billing_postal_code")}
          withAsterisk
          disabled={disabled}
          {...form.getInputProps("billing_postal_code")}
        />
      </SimpleGrid>
      <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
        <TextInput
          id={profileFieldId("billing_city")}
          label={t("company_profile_form.billing_city")}
          withAsterisk
          disabled={disabled}
          {...form.getInputProps("billing_city")}
        />
        <SearchSelect
          id={profileFieldId("billing_country")}
          label={t("company_profile_form.billing_country")}
          placeholder={t("company_profile_form.billing_country_placeholder")}
          data={countryOptions}
          withAsterisk
          nothingFoundMessage={t("company_profile_form.no_match")}
          clearable
          disabled={disabled}
          value={form.values.billing_country}
          error={form.errors.billing_country}
          onChange={(value) =>
            form.setFieldValue("billing_country", value ?? "")
          }
        />
      </SimpleGrid>
      <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
        <TextInput
          id={profileFieldId("billing_vat_number")}
          label={t("company_profile_form.billing_vat_number")}
          disabled={disabled}
          {...form.getInputProps("billing_vat_number")}
        />
        <TextInput
          id={profileFieldId("billing_email")}
          label={t("company_profile_form.billing_email")}
          withAsterisk
          autoComplete="email"
          disabled={disabled}
          {...form.getInputProps("billing_email")}
        />
      </SimpleGrid>
    </Stack>
  );
};

export default CompanyBillingFields;
