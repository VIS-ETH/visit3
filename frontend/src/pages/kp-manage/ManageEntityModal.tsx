import { Button, Group, Modal, Stack } from "@mantine/core";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

interface ManageEntityModalProps {
  opened: boolean;
  onClose: () => void;
  title: string;
  isSaving: boolean;
  isSubmitDisabled?: boolean;
  submitLabel: string;
  onSubmit: () => void;
  children: ReactNode;
}

export default function ManageEntityModal({
  opened,
  onClose,
  title,
  isSaving,
  isSubmitDisabled = false,
  submitLabel,
  onSubmit,
  children,
}: ManageEntityModalProps) {
  const { t } = useTranslation();

  return (
    <Modal opened={opened} onClose={onClose} title={title} centered>
      <Stack gap="sm">
        {children}
        <Group justify="flex-end">
          <Button variant="default" onClick={onClose} disabled={isSaving}>
            {t("common.cancel")}
          </Button>
          <Button
            loading={isSaving}
            disabled={isSubmitDisabled}
            onClick={onSubmit}
          >
            {submitLabel}
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
