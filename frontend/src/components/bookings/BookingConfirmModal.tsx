import { Button, Group, Modal, Stack, Text } from "@mantine/core";
import { useTranslation } from "react-i18next";

const BookingConfirmModal = ({
  body,
  color,
  isPending,
  onClose,
  onConfirm,
  opened,
  submitLabel,
  title,
}: {
  body: string;
  color?: string;
  isPending: boolean;
  onClose: () => void;
  onConfirm: () => void;
  opened: boolean;
  submitLabel: string;
  title: string;
}) => {
  const { t } = useTranslation();

  return (
    <Modal centered onClose={onClose} opened={opened} title={title}>
      <Stack gap="md">
        <Text size="sm">{body}</Text>
        <Group justify="flex-end">
          <Button disabled={isPending} onClick={onClose} variant="subtle">
            {t("common.cancel")}
          </Button>
          <Button color={color} loading={isPending} onClick={onConfirm}>
            {submitLabel}
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
};

export default BookingConfirmModal;
