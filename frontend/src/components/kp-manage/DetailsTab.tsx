import { Button, Group, Paper, Stack, Title } from "@mantine/core";
import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import {
  kpFormValuesFromEvent,
  toKpWithSettingsRequest,
  type KpWithSettingsFormValues,
} from "../../schemas/eventSettingsSchema";
import { notifySuccess } from "../../utils/notify";
import { useCurrentUser } from "../../context/useCurrentUser";
import { useAsyncAction } from "../../hooks/use-async-action";
import ErrorAlert from "../ErrorAlert";
import PageLoader from "../PageLoader";
import EventBannerSection from "./EventBannerSection";
import EventFormFields from "./EventFormFields";
import { useEventForm } from "./use-event-form";
import {
  getGetKpByIdQueryKey,
  getGetKpSettingsQueryKey,
  getListKpsQueryKey,
  useGetKpById,
  useGetKpSettings,
  useUpdateKp,
} from "../../orval/generated/kp/kp";

const DetailsTab = ({ eventId }: { eventId: string }) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { user } = useCurrentUser();
  const isPresident = user?.is_kp_president ?? false;
  const eventQuery = useGetKpById(eventId);
  const settingsQuery = useGetKpSettings(eventId, {
    query: { enabled: isPresident },
  });
  const event = eventQuery.data;
  const settings = settingsQuery.data;
  const settingsSettled = !isPresident || !settingsQuery.isPending;
  const initialisedEventIdRef = useRef<string | null>(null);
  const form = useEventForm();
  const { mutateAsync: updateKp } = useUpdateKp();

  useEffect(() => {
    if (!event || !settingsSettled) return;
    if (initialisedEventIdRef.current === event.id) return;
    initialisedEventIdRef.current = event.id;
    const values = kpFormValuesFromEvent(event, settings);
    form.setInitialValues(values);
    form.setValues(values);
    form.resetDirty();
    form.clearErrors();
  }, [event, settings, settingsSettled, form]);

  const { run: save, isRunning: isSaving } = useAsyncAction(
    async (values: KpWithSettingsFormValues) => {
      const { notification_email, ...request } =
        toKpWithSettingsRequest(values);
      await updateKp({
        eventId,
        data: settings ? { ...request, notification_email } : request,
      });
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: getGetKpByIdQueryKey(eventId),
        }),
        queryClient.invalidateQueries({
          queryKey: getGetKpSettingsQueryKey(eventId),
        }),
        queryClient.invalidateQueries({ queryKey: getListKpsQueryKey() }),
      ]);
      notifySuccess(t("kp.manage.edit_success"));
    },
  );

  if (eventQuery.isError) return <ErrorAlert />;
  if (!event || !settingsSettled) return <PageLoader />;

  return (
    <Stack gap="lg">
      {settingsQuery.isError ? <ErrorAlert /> : null}
      <Paper withBorder p="lg" radius="md">
        <form onSubmit={form.onSubmit((values) => void save(values))}>
          <Stack gap="md">
            <Title order={4}>{t("kp.manage.edit_title")}</Title>
            <EventFormFields
              form={form}
              disabled={!isPresident || isSaving}
              showNotificationEmail={Boolean(settings)}
            />
            {isPresident ? (
              <Group justify="flex-end">
                <Button
                  type="submit"
                  loading={isSaving}
                  disabled={!form.isValid()}
                >
                  {t("kp.manage.save")}
                </Button>
              </Group>
            ) : null}
          </Stack>
        </form>
      </Paper>
      {isPresident ? (
        <Paper withBorder p="lg" radius="md">
          <EventBannerSection eventId={eventId} />
        </Paper>
      ) : null}
    </Stack>
  );
};
export default DetailsTab;
