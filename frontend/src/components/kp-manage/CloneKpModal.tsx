import { Button, Group, Modal, Select, Stack } from "@mantine/core";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";
import type { KpResponse } from "../../orval/generated/fastAPI.schemas";
import { getListKpsQueryKey, useCloneKp } from "../../orval/generated/kp/kp";
import {
  toKpWithSettingsRequest,
  type KpWithSettingsFormValues,
} from "../../schemas/eventSettingsSchema";
import { useAsyncAction } from "../../hooks/use-async-action";
import { notifySuccess } from "../../utils/notify";
import EventFormFields from "./EventFormFields";
import { useEventForm } from "./use-event-form";

const CloneKpModal = ({
  eventId,
  sourceEvents,
  opened,
  onClose,
}: {
  eventId: string;
  sourceEvents?: readonly KpResponse[];
  opened: boolean;
  onClose: () => void;
}) => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [pickedSourceId, setPickedSourceId] = useState<string | null>(null);
  const sourceId = pickedSourceId ?? eventId;
  const form = useEventForm();
  const { mutateAsync: cloneKp } = useCloneKp();

  const closeAndReset = () => {
    form.reset();
    setPickedSourceId(null);
    onClose();
  };

  const { run: clone, isRunning } = useAsyncAction(
    async (values: KpWithSettingsFormValues) => {
      const clonedEvent = await cloneKp({
        eventId: sourceId,
        data: toKpWithSettingsRequest(values),
      });
      await queryClient.invalidateQueries({ queryKey: getListKpsQueryKey() });
      notifySuccess(t("kp.manage.clone_success"));
      closeAndReset();
      navigate(`/kp/${clonedEvent.id}`);
    },
  );

  return (
    <Modal
      opened={opened}
      onClose={isRunning ? () => undefined : closeAndReset}
      title={t("kp.manage.clone_title")}
      size="lg"
      centered
    >
      <form onSubmit={form.onSubmit((values) => void clone(values))}>
        <Stack gap="sm">
          {sourceEvents ? (
            <Select
              label={t("kp.dashboard.copy_source")}
              data={sourceEvents.map((event) => ({
                value: event.id,
                label: event.name,
              }))}
              value={sourceId}
              onChange={(value) => setPickedSourceId(value)}
              allowDeselect={false}
              disabled={isRunning}
            />
          ) : null}
          <EventFormFields form={form} disabled={isRunning} />
          <Group justify="flex-end">
            <Button
              variant="default"
              onClick={closeAndReset}
              disabled={isRunning}
            >
              {t("common.cancel")}
            </Button>
            <Button
              type="submit"
              loading={isRunning}
              disabled={!form.isValid()}
            >
              {t("kp.manage.clone_submit")}
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
};

export default CloneKpModal;
