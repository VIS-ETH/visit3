import { Button, Group, Modal, Stack } from "@mantine/core";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { useAsyncAction } from "../../hooks/use-async-action";

const BookingActionModal = ({
  children,
  color,
  isSubmitDisabled = false,
  onClose,
  onSubmit,
  opened,
  submitLabel,
  title,
}: {
  children: (isSubmitting: boolean) => ReactNode;
  color?: string;
  isSubmitDisabled?: boolean;
  onClose: () => void;
  onSubmit: () => Promise<unknown> | void;
  opened: boolean;
  submitLabel: string;
  title: string;
}) => {
  const { t } = useTranslation();
  const { run, isRunning } = useAsyncAction(async () => {
    await onSubmit();
  });

  return (
    <Modal
      centered
      onClose={isRunning ? () => undefined : onClose}
      opened={opened}
      title={title}
    >
      <Stack gap="md">
        {children(isRunning)}
        <Group justify="flex-end">
          <Button disabled={isRunning} onClick={onClose} variant="subtle">
            {t("common.cancel")}
          </Button>
          <Button
            color={color}
            disabled={isSubmitDisabled}
            loading={isRunning}
            onClick={() => {
              void run();
            }}
          >
            {submitLabel}
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
};

export default BookingActionModal;
