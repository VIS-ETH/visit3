import { Button, Group, Modal, Stack, Text } from "@mantine/core";
import { useTranslation } from "react-i18next";

interface MailTemplateResetModalProps {
  opened: boolean;
  templateKey: string;
  isPending: boolean;
  onConfirm: () => void;
  onClose: () => void;
}

const MailTemplateResetModal = ({
  opened,
  templateKey,
  isPending,
  onConfirm,
  onClose,
}: MailTemplateResetModalProps) => {
  const { t } = useTranslation();

  return (
    <Modal
      centered
      closeOnClickOutside={!isPending}
      closeOnEscape={!isPending}
      onClose={onClose}
      opened={opened}
      title={t("mail_templates.reset_modal.title")}
      withCloseButton={!isPending}
    >
      <Stack gap="sm">
        <Text>
          {t("mail_templates.reset_modal.message", { key: templateKey })}
        </Text>
        <Text c="dimmed" size="sm">
          {t("mail_templates.reset_modal.hint")}
        </Text>
        <Group justify="flex-end" mt="md">
          <Button disabled={isPending} onClick={onClose} variant="default">
            {t("mail_templates.reset_modal.cancel")}
          </Button>
          <Button color="red" loading={isPending} onClick={onConfirm}>
            {t("mail_templates.reset_modal.confirm")}
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
};
export default MailTemplateResetModal;
