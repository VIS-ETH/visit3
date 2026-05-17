import {
  Button,
  Group,
  Paper,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useQueryClient } from "@tanstack/react-query";
import type { ChangeEvent } from "react";
import { useTranslation } from "react-i18next";
import { kpSchema, type KpFormValues } from "../schemas/kpSchema";
import { formatKpDateInput, toKpIsoDate } from "../utils/kp-utils";
import { useTranslatedForm } from "../utils/translator";
import {
  getGetKpByIdQueryKey,
  getListKpsQueryKey,
  useGetKpById,
  useUpdateKp,
} from "../orval/generated/kp/kp";

const dateFieldNames = [
  "registrationOpen",
  "registrationEnd",
  "finalizationDeadline",
  "nametagsDeadline",
  "eventDate",
] as const;

const DetailsTab = ({ eventId }: { eventId: string }) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data: event } = useGetKpById(eventId);

  const form = useTranslatedForm<typeof kpSchema>(kpSchema, {
    initialValues: {
      name: event?.name ?? "",
      registrationOpen: event?.registration_open
        ? formatKpDateInput(new Date(event.registration_open))
        : "",
      registrationEnd: event?.registration_end
        ? formatKpDateInput(new Date(event.registration_end))
        : "",
      finalizationDeadline: event?.finalization_deadline
        ? formatKpDateInput(new Date(event.finalization_deadline))
        : "",
      nametagsDeadline: event?.nametags_deadline
        ? formatKpDateInput(new Date(event.nametags_deadline))
        : "",
      eventDate: event?.event_date
        ? formatKpDateInput(new Date(event.event_date))
        : "",
    },
    validateInputOnChange: true,
  });

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

  const { mutate: update, isPending } = useUpdateKp({
    mutation: {
      onSuccess: async () => {
        await queryClient.invalidateQueries({
          queryKey: getGetKpByIdQueryKey(eventId),
        });
        await queryClient.invalidateQueries({ queryKey: getListKpsQueryKey() });
        notifications.show({
          color: "green",
          message: t("kp.manage.edit_success"),
        });
      },
    },
  });

  const handleSubmit = (values: KpFormValues) => {
    update({
      eventId,
      data: {
        name: values.name.trim(),
        registration_open: toKpIsoDate(values.registrationOpen),
        registration_end: toKpIsoDate(values.registrationEnd),
        finalization_deadline: toKpIsoDate(values.finalizationDeadline),
        nametags_deadline: toKpIsoDate(values.nametagsDeadline),
        event_date: toKpIsoDate(values.eventDate),
      },
    });
  };

  return (
    <Paper withBorder p="lg" radius="md">
      <form onSubmit={form.onSubmit(handleSubmit)}>
        <Stack gap="md">
          <div>
            <Title order={4}>{t("kp.manage.edit_title")}</Title>
            <Text c="dimmed" size="sm">
              {t("kp.dashboard.date_input_hint")}
            </Text>
          </div>
          <SimpleGrid
            cols={{ base: 1, md: 2 }}
            spacing="md"
            verticalSpacing="sm"
          >
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
          <Group justify="flex-end">
            <Button
              type="submit"
              loading={isPending}
              disabled={isPending || !form.isValid()}
            >
              {t("kp.manage.save")}
            </Button>
          </Group>
        </Stack>
      </form>
    </Paper>
  );
};
export default DetailsTab;
