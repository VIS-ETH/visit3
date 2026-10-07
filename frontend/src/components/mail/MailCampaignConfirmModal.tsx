import { Button, Group, Modal, Stack } from "@mantine/core";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

interface MailCampaignConfirmModalProps {
  opened: boolean;
  title: string;
  confirmLabel: string;
  confirmColor?: string;
  confirmDisabled?: boolean;
  isPending: boolean;
  onConfirm: () => void;
  onClose: () => void;
  children: ReactNode;
}

const MailCampaignConfirmModal = ({
  opened,
  title,
  confirmLabel,
  confirmColor,
  confirmDisabled,
  isPending,
  onConfirm,
  onClose,
  children,
}: MailCampaignConfirmModalProps) => {
  const { t } = useTranslation();

  return (
    <Modal
      centered
      closeOnClickOutside={!isPending}
      closeOnEscape={!isPending}
      onClose={onClose}
      opened={opened}
      title={title}
      withCloseButton={!isPending}
    >
      <Stack gap="sm">
        {children}
        <Group justify="flex-end" mt="md">
          <Button disabled={isPending} onClick={onClose} variant="default">
            {t("mail_campaigns.cancel")}
          </Button>
          <Button
            color={confirmColor}
            disabled={confirmDisabled}
            loading={isPending}
            onClick={onConfirm}
          >
            {confirmLabel}
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
};
export default MailCampaignConfirmModal;
