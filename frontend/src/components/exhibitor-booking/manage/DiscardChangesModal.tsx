import { Button, Group, Modal, Stack, Text } from "@mantine/core";
import { useTranslation } from "react-i18next";

const DiscardChangesModal = ({
  onDiscard,
  onStay,
  opened,
}: {
  onDiscard: () => void;
  onStay: () => void;
  opened: boolean;
}) => {
  const { t } = useTranslation();

  return (
    <Modal
      centered
      opened={opened}
      onClose={onStay}
      title={t("kp.booking_manage.discard_changes_title")}
    >
      <Stack gap="md">
        <Text size="sm">{t("kp.booking_manage.discard_changes_body")}</Text>
        <Group justify="flex-end">
          <Button variant="subtle" onClick={onStay}>
            {t("kp.booking_manage.stay_on_page")}
          </Button>
          <Button color="red" onClick={onDiscard}>
            {t("kp.booking_manage.discard_changes_submit")}
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
};

export default DiscardChangesModal;
