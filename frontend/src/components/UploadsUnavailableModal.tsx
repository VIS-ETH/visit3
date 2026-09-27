import { Button, Group, Modal, Stack, Text } from "@mantine/core";
import { useTranslation } from "react-i18next";

interface UploadsUnavailableModalProps {
  opened: boolean;
  onClose: () => void;
}

const UploadsUnavailableModal = ({
  opened,
  onClose,
}: UploadsUnavailableModalProps) => {
  const { t } = useTranslation();

  return (
    <Modal
      centered
      opened={opened}
      onClose={onClose}
      title={t("uploads.unavailable_title")}
    >
      <Stack gap="md">
        <Text size="sm">{t("uploads.unavailable_body")}</Text>
        <Group justify="flex-end">
          <Button onClick={onClose}>{t("common.ok")}</Button>
        </Group>
      </Stack>
    </Modal>
  );
};

export default UploadsUnavailableModal;
