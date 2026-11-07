import { Button, Group, Modal, Stack } from "@mantine/core";
import { IconDeviceFloppy } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import type { BookingServiceResponse } from "../../../orval/generated/fastAPI.schemas";
import BookedServiceCard from "./BookedServiceCard";
import type { RequirementChanges } from "./use-requirement-changes";

const RequirementsPromptModal = ({
  bookingServices,
  changes,
  editable,
  onClose,
  onSave,
  promptedChangeCount,
}: {
  bookingServices: BookingServiceResponse[];
  changes: RequirementChanges;
  editable: boolean;
  onClose: () => void;
  onSave: () => void;
  promptedChangeCount: number;
}) => {
  const { t } = useTranslation();

  return (
    <Modal
      centered
      size="xl"
      opened={bookingServices.length > 0}
      onClose={onClose}
      title={t("kp.booking_manage.requirements_prompt_title")}
    >
      <Stack gap="md">
        {bookingServices.map((bookingService) => (
          <BookedServiceCard
            bookingService={bookingService}
            changes={changes}
            editable={editable}
            key={bookingService.id}
          />
        ))}
        <Group justify="flex-end">
          <Button variant="subtle" onClick={onClose}>
            {t("kp.booking_manage.requirements_prompt_later")}
          </Button>
          <Button
            disabled={promptedChangeCount === 0}
            leftSection={<IconDeviceFloppy size={16} />}
            loading={changes.isSaving}
            onClick={onSave}
          >
            {t("kp.booking_manage.requirements_prompt_save")}
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
};

export default RequirementsPromptModal;
