import { Alert, Anchor, Group, Stack, Text } from "@mantine/core";
import { IconAlertTriangle } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import {
  mandatoryFieldLabelKey,
  profileFieldId,
} from "./company-profile-fields";

interface CompanyProfileMissingFieldsProps {
  fields: string[];
}

const CompanyProfileMissingFields = ({
  fields,
}: CompanyProfileMissingFieldsProps) => {
  const { t } = useTranslation();

  if (fields.length === 0) return null;

  return (
    <Alert
      icon={<IconAlertTriangle />}
      color="orange"
      title={t("company_profile_form.missing_title")}
    >
      <Stack gap="xs">
        <Text size="sm">{t("company_profile_form.missing_description")}</Text>
        <Group gap="sm">
          {fields.map((field) => (
            <Anchor
              key={field}
              size="sm"
              href={`#${profileFieldId(field)}`}
              onClick={() =>
                document.getElementById(profileFieldId(field))?.focus()
              }
            >
              {t(mandatoryFieldLabelKey(field))}
            </Anchor>
          ))}
        </Group>
      </Stack>
    </Alert>
  );
};

export default CompanyProfileMissingFields;
