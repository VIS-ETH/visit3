import {
  Button,
  Divider,
  Group,
  Modal,
  Select,
  SimpleGrid,
  Stack,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useQueryClient } from "@tanstack/react-query";
import { type ChangeEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";
import type { KpResponse } from "../../orval/generated/fastAPI.schemas";
import { getListKpsQueryKey, useCloneKp } from "../../orval/generated/kp/kp";
import {
  emptyEventSettingsValues,
  kpWithSettingsSchema,
  toKpWithSettingsRequest,
  type KpWithSettingsFormValues,
} from "../../schemas/eventSettingsSchema";
import { useTranslatedForm } from "../../utils/translator";
import EventSettingsFields from "./EventSettingsFields";

const dateFieldNames = [
  "registrationOpen",
  "registrationEnd",
  "finalizationDeadline",
  "nametagsDeadline",
  "eventDate",
] as const;

const emptyKpFormValues: KpWithSettingsFormValues = {
  name: "",
  registrationOpen: "",
  registrationEnd: "",
  finalizationDeadline: "",
  nametagsDeadline: "",
  eventDate: "",
  ...emptyEventSettingsValues,
};

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
  const form = useTranslatedForm<typeof kpWithSettingsSchema>(
    kpWithSettingsSchema,
    {
      initialValues: emptyKpFormValues,
    },
  );

  const { mutate: clone, isPending } = useCloneKp({
    mutation: {
      onSuccess: async (clonedEvent) => {
        await queryClient.invalidateQueries({ queryKey: getListKpsQueryKey() });
        notifications.show({
          color: "green",
          message: t("kp.manage.clone_success"),
        });
        form.setValues(emptyKpFormValues);
        setPickedSourceId(null);
        onClose();
        navigate(`/kp/${clonedEvent.id}`);
      },
    },
  });

  const closeAndReset = () => {
    form.setValues(emptyKpFormValues);
    setPickedSourceId(null);
    onClose();
  };

  const getDateInputProps = (field: (typeof dateFieldNames)[number]) => {
    const inputProps = form.getInputProps(field);
    return {
      ...inputProps,
      onChange: (e: ChangeEvent<HTMLInputElement>) => {
        inputProps.onChange(e);
        for (const f of dateFieldNames) form.validateField(f);
      },
    };
  };

  const handleSubmit = (values: KpWithSettingsFormValues) => {
    clone({
      eventId: sourceId,
      data: toKpWithSettingsRequest(values),
    });
  };

  return (
    <Modal
      opened={opened}
      onClose={closeAndReset}
      title={t("kp.manage.clone_title")}
      centered
    >
      <form onSubmit={form.onSubmit(handleSubmit)}>
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
              disabled={isPending}
            />
          ) : null}
          <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
            <TextInput
              label={t("kp.dashboard.name")}
              disabled={isPending}
              {...form.getInputProps("name")}
            />
            <TextInput
              label={t("kp.dashboard.registration_open")}
              placeholder={t("kp.dashboard.date_input_placeholder")}
              disabled={isPending}
              {...getDateInputProps("registrationOpen")}
            />
            <TextInput
              label={t("kp.dashboard.registration_end")}
              placeholder={t("kp.dashboard.date_input_placeholder")}
              disabled={isPending}
              {...getDateInputProps("registrationEnd")}
            />
            <TextInput
              label={t("kp.dashboard.finalization_deadline")}
              placeholder={t("kp.dashboard.date_input_placeholder")}
              disabled={isPending}
              {...getDateInputProps("finalizationDeadline")}
            />
            <TextInput
              label={t("kp.dashboard.nametags_deadline")}
              placeholder={t("kp.dashboard.date_input_placeholder")}
              disabled={isPending}
              {...getDateInputProps("nametagsDeadline")}
            />
            <TextInput
              label={t("kp.dashboard.event_date")}
              placeholder={t("kp.dashboard.date_input_placeholder")}
              disabled={isPending}
              {...getDateInputProps("eventDate")}
            />
          </SimpleGrid>
          <Divider />
          <EventSettingsFields
            disabled={isPending}
            getInputProps={(field) => form.getInputProps(field)}
          />
          <Group justify="flex-end">
            <Button
              variant="default"
              onClick={closeAndReset}
              disabled={isPending}
            >
              {t("common.cancel")}
            </Button>
            <Button
              type="submit"
              loading={isPending}
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
