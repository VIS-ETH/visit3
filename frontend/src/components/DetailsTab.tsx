import {
  Button,
  Divider,
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
import { useEffect, useRef, type ChangeEvent } from "react";
import { useTranslation } from "react-i18next";
import {
  emptyEventSettingsValues,
  kpWithSettingsSchema,
  toKpWithSettingsRequest,
  type KpWithSettingsFormValues,
} from "../schemas/eventSettingsSchema";
import { formatKpIsoDateInput } from "../utils/kp-utils";
import { useTranslatedForm } from "../utils/translator";
import { useCurrentUser } from "../context/useCurrentUser";
import EventSettingsFields from "./kp/EventSettingsFields";
import {
  getGetKpByIdQueryKey,
  getGetKpSettingsQueryKey,
  getListKpsQueryKey,
  useGetKpById,
  useGetKpSettings,
  useUpdateKp,
} from "../orval/generated/kp/kp";

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

const DetailsTab = ({ eventId }: { eventId: string }) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { user } = useCurrentUser();
  const isPresident = user?.is_kp_president ?? false;
  const { data: event } = useGetKpById(eventId);
  const { data: settings } = useGetKpSettings(eventId, {
    query: { enabled: isPresident },
  });
  const initialisedEventIdRef = useRef<string | null>(null);

  const form = useTranslatedForm<typeof kpWithSettingsSchema>(
    kpWithSettingsSchema,
    {
      initialValues: emptyKpFormValues,
    },
  );

  useEffect(() => {
    if (!event || initialisedEventIdRef.current === event.id) return;
    if (isPresident && !settings) return;
    initialisedEventIdRef.current = event.id;
    const values: KpWithSettingsFormValues = {
      name: event.name,
      registrationOpen: formatKpIsoDateInput(event.registration_open),
      registrationEnd: formatKpIsoDateInput(event.registration_end),
      finalizationDeadline: formatKpIsoDateInput(event.finalization_deadline),
      nametagsDeadline: formatKpIsoDateInput(event.nametags_deadline),
      eventDate: formatKpIsoDateInput(event.event_date),
      vatRatePercent: event.vat_rate_percent,
      termsUrl: event.terms_url ?? "",
      notificationEmail: settings?.notification_email ?? "",
      finalizationReminderDays: event.finalization_reminder_days,
    };
    form.setInitialValues(values);
    form.setValues(values);
    form.resetDirty();
    form.clearErrors();
  }, [event, settings, isPresident, form]);

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
        await queryClient.invalidateQueries({
          queryKey: getGetKpSettingsQueryKey(eventId),
        });
        await queryClient.invalidateQueries({ queryKey: getListKpsQueryKey() });
        notifications.show({
          color: "green",
          message: t("kp.manage.edit_success"),
        });
      },
    },
  });

  const handleSubmit = (values: KpWithSettingsFormValues) => {
    update({
      eventId,
      data: toKpWithSettingsRequest(values),
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
          <Divider />
          <EventSettingsFields
            disabled={isPending}
            getInputProps={(field) => form.getInputProps(field)}
          />
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
