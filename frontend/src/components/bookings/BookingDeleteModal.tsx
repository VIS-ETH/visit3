import { Button, Checkbox, Group, Modal, Stack, Text } from "@mantine/core";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

const BookingDeleteModal = ({
  isPending,
  onClose,
  onConfirm,
  opened,
  requiresForce,
}: {
  isPending: boolean;
  onClose: () => void;
  onConfirm: (force: boolean) => void;
  opened: boolean;
  requiresForce: boolean;
}) => {
  const { t } = useTranslation();
  const [force, setForce] = useState(false);

  useEffect(() => {
    if (!opened) setForce(false);
  }, [opened]);

  return (
    <Modal
      centered
      onClose={onClose}
      opened={opened}
      title={t("kp.manage.booking_delete_title")}
    >
      <Stack gap="md">
        <Text size="sm">{t("kp.manage.booking_delete_body")}</Text>
        {requiresForce ? (
          <Checkbox
            checked={force}
            label={t("kp.manage.booking_delete_force")}
            onChange={(event) => setForce(event.currentTarget.checked)}
          />
        ) : null}
        <Group justify="flex-end">
          <Button disabled={isPending} onClick={onClose} variant="subtle">
            {t("common.cancel")}
          </Button>
          <Button
            color="red"
            disabled={requiresForce && !force}
            loading={isPending}
            onClick={() => onConfirm(force)}
          >
            {t("kp.manage.booking_delete_submit")}
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
};

export default BookingDeleteModal;
