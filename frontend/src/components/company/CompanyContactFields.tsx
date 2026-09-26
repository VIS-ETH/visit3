import { SimpleGrid, Stack, TextInput } from "@mantine/core";
import { useTranslation } from "react-i18next";
import type { UserResponse } from "../../orval/generated/fastAPI.schemas";
import { getDisplayName } from "../../utils/display";
import {
  profileFieldId,
  type CompanyProfileFieldsProps,
} from "./company-profile-fields";
import SearchSelect from "../SearchSelect";

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
      <SearchSelect
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
        withAsterisk
        nothingFoundMessage={t("company_profile_form.no_match")}
        clearable
        disabled={disabled}
        value={form.values.kp_contact_user_id}
        error={form.errors.kp_contact_user_id}
        onChange={(value) =>
          form.setFieldValue("kp_contact_user_id", value ?? "")
        }
      />
      <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
        <TextInput
          id={profileFieldId("general_email")}
          label={t("company_profile_form.general_email")}
          placeholder={t("company_profile_form.general_email_placeholder")}
          withAsterisk
          autoComplete="email"
          disabled={disabled}
          {...form.getInputProps("general_email")}
        />
        <TextInput
          id={profileFieldId("general_phone")}
          label={t("company_profile_form.general_phone")}
          disabled={disabled}
          {...form.getInputProps("general_phone")}
        />
      </SimpleGrid>
    </Stack>
  );
};

export default CompanyContactFields;
