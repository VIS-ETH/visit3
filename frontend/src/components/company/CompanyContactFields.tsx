import { Select, SimpleGrid, Stack, TextInput } from "@mantine/core";
import { useTranslation } from "react-i18next";
import type { UserResponse } from "../../orval/generated/fastAPI.schemas";
import { getDisplayName } from "../../utils/display";
import {
  profileFieldId,
  type CompanyProfileFieldsProps,
} from "./company-profile-fields";

interface CompanyContactFieldsProps extends CompanyProfileFieldsProps {
  members: UserResponse[];
}

const CompanyContactFields = ({
  form,
  disabled,
  members,
}: CompanyContactFieldsProps) => {
  const { t } = useTranslation();

  return (
    <Stack gap="md">
      <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
        <TextInput
          id={profileFieldId("contact_person")}
          label={t("company_profile_form.contact_person")}
          withAsterisk
          disabled={disabled}
          {...form.getInputProps("contact_person")}
        />
        <TextInput
          id={profileFieldId("contact_email")}
          label={t("company_profile_form.contact_email")}
          withAsterisk
          autoComplete="email"
          disabled={disabled}
          {...form.getInputProps("contact_email")}
        />
      </SimpleGrid>
      <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
        <TextInput
          id={profileFieldId("contact_phone")}
          label={t("company_profile_form.contact_phone")}
          disabled={disabled}
          {...form.getInputProps("contact_phone")}
        />
        <Select
          id={profileFieldId("kp_contact_user_id")}
          label={t("company_profile_form.kp_contact_user")}
          placeholder={t("company_profile_form.kp_contact_user_placeholder")}
          description={t("company_profile_form.kp_contact_user_hint")}
          data={members.map((member) => ({
            value: member.id,
            label: getDisplayName(
              member.first_name,
              member.last_name,
              member.email,
            ),
          }))}
          searchable
          clearable
          disabled={disabled}
          value={form.values.kp_contact_user_id}
          error={form.errors.kp_contact_user_id}
          onChange={(value) =>
            form.setFieldValue("kp_contact_user_id", value ?? "")
          }
        />
      </SimpleGrid>
    </Stack>
  );
};

export default CompanyContactFields;
