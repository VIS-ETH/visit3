import { Alert, Button, Group, Text } from "@mantine/core";
import { IconDeviceFloppy } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";

const ProfileDraftNotice = ({ onDiscard }: { onDiscard: () => void }) => {
  const { t } = useTranslation();

  return (
    <Alert
      color="blue"
      icon={<IconDeviceFloppy />}
      title={t("company_profile_form.draft_restored_title")}
    >
      <Group justify="space-between" gap="sm" wrap="wrap">
        <Text size="sm">{t("company_profile_form.draft_restored")}</Text>
        <Button size="xs" variant="default" onClick={onDiscard}>
          {t("company_profile_form.discard")}
        </Button>
      </Group>
    </Alert>
  );
};

export default ProfileDraftNotice;
