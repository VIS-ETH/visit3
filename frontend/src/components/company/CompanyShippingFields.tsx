import { Textarea } from "@mantine/core";
import { useTranslation } from "react-i18next";
import {
  profileFieldId,
  type CompanyProfileFieldsProps,
} from "./company-profile-fields";

const CompanyShippingFields = ({
  form,
  disabled,
}: CompanyProfileFieldsProps) => {
  const { t } = useTranslation();

  return (
    <Textarea
      id={profileFieldId("shipping_address")}
      label={t("company_profile_form.shipping_address")}
      description={t("company_profile_form.shipping_address_hint")}
      placeholder={t("company_profile_form.shipping_address_placeholder")}
      autosize
      minRows={3}
      maxRows={6}
      disabled={disabled}
      {...form.getInputProps("shipping_address")}
    />
  );
};

export default CompanyShippingFields;
