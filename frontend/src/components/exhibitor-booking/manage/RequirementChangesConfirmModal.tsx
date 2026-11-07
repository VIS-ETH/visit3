import { Badge, Button, Group, Modal, Stack, Text } from "@mantine/core";
import { IconDeviceFloppy } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import {
  changeKey,
  requirementChangeLabel,
  type PendingRequirementChange,
} from "./requirement-changes";

const RequirementChangesConfirmModal = ({
  changes,
  isSaving,
  onClose,
  onSubmit,
  opened,
}: {
  changes: PendingRequirementChange[];
  isSaving: boolean;
  onClose: () => void;
  onSubmit: () => void;
  opened: boolean;
}) => {
  const { t } = useTranslation();

  return (
    <Modal
      centered
      opened={opened}
      onClose={onClose}
      title={t("kp.booking_manage.confirm_requirement_changes_title")}
    >
      <Stack gap="md">
        <Text size="sm">
          {t("kp.booking_manage.confirm_requirement_changes_body")}
        </Text>
        <Stack gap="xs">
          {changes.map((change) => (
            <Group justify="space-between" key={changeKey(change)}>
              <div>
                <Text size="sm" fw={600}>
                  {change.serviceName}
                </Text>
                <Text size="xs" c="dimmed">
                  {change.requirementName}
                </Text>
              </div>
              <Badge variant="light">{requirementChangeLabel(change, t)}</Badge>
            </Group>
          ))}
        </Stack>
        <Group justify="flex-end">
          <Button variant="subtle" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button
            leftSection={<IconDeviceFloppy size={16} />}
            loading={isSaving}
            onClick={onSubmit}
          >
            {t("kp.booking_manage.confirm_requirement_changes_submit")}
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
};

export default RequirementChangesConfirmModal;
