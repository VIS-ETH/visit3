import { SimpleGrid, Switch } from "@mantine/core";
import { useTranslation } from "react-i18next";
import {
  profileFieldId,
  type CompanyProfileFieldsProps,
} from "./company-profile-fields";

const CompanyOfferFields = ({ form, disabled }: CompanyProfileFieldsProps) => {
  const { t } = useTranslation();

  return (
    <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md" verticalSpacing="sm">
      <Switch
        id={profileFieldId("offers_internships")}
        label={t("company_profile_form.offers_internships")}
        disabled={disabled}
        {...form.getInputProps("offers_internships", { type: "checkbox" })}
      />
      <Switch
        id={profileFieldId("offers_part_time")}
        label={t("company_profile_form.offers_part_time")}
        disabled={disabled}
        {...form.getInputProps("offers_part_time", { type: "checkbox" })}
      />
      <Switch
        id={profileFieldId("offers_theses")}
        label={t("company_profile_form.offers_theses")}
        disabled={disabled}
        {...form.getInputProps("offers_theses", { type: "checkbox" })}
      />
      <Switch
        id={profileFieldId("offers_graduate_positions")}
        label={t("company_profile_form.offers_graduate_positions")}
        disabled={disabled}
        {...form.getInputProps("offers_graduate_positions", {
          type: "checkbox",
        })}
      />
    </SimpleGrid>
  );
};

export default CompanyOfferFields;
