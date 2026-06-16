import {
  Button,
  Group,
  Paper,
  Select,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, type ChangeEvent } from "react";
import { useTranslation } from "react-i18next";
import { kpSchema, toKpRequest, type KpFormValues } from "../schemas/kpSchema";
import { formatKpDateInput } from "../utils/kp-utils";
import { useTranslatedForm } from "../utils/translator";
import { KpEventServiceRequirementType } from "../orval/generated/fastAPI.schemas";
import {
  getGetKpByIdQueryKey,
  getListKpsQueryKey,
  getListServicesQueryKey,
  type GetKpByIdQueryResult,
  useGetKpById,
  useListServices,
  useSetAdvertisementService,
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

  const initialValues = useMemo(
    () => ({
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
    }),
    [event],
  );

  const form = useTranslatedForm<typeof kpSchema>(kpSchema, {
    initialValues,
    validateInputOnChange: true,
  });

  useEffect(() => {
    if (!event) return;
    form.setValues(initialValues);
    form.resetDirty(initialValues);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [event, initialValues]);

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
      data: toKpRequest(values),
    });
  };

  return (
    <Stack gap="md">
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
    <AdvertisementServiceSection event={event} eventId={eventId} />
    </Stack>
  );
};

const AdvertisementServiceSection = ({
  event,
  eventId,
}: {
  event: GetKpByIdQueryResult | undefined;
  eventId: string;
}) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data: services = [] } = useListServices(eventId);

  const eligibleServices = useMemo(
    () =>
      services.filter(
        (service) =>
          service.requirements.length === 1 &&
          service.requirements[0].type ===
            KpEventServiceRequirementType.pdf_single_page &&
          service.max_quantity_per_booking === 1,
      ),
    [services],
  );

  const { mutate: setAd, isPending } = useSetAdvertisementService({
    mutation: {
      onSuccess: async () => {
        await queryClient.invalidateQueries({
          queryKey: getGetKpByIdQueryKey(eventId),
        });
        await queryClient.invalidateQueries({
          queryKey: getListServicesQueryKey(eventId),
        });
        notifications.show({
          color: "green",
          message: t("kp.manage.advertisement_service_saved"),
        });
      },
      onError: () => {
        notifications.show({
          color: "red",
          message: t("kp.manage.advertisement_service_save_error"),
        });
      },
    },
  });

  return (
    <Paper withBorder p="lg" radius="md">
      <Stack gap="md">
        <div>
          <Title order={4}>{t("kp.manage.advertisement_service_title")}</Title>
          <Text c="dimmed" size="sm">
            {t("kp.manage.advertisement_service_description")}
          </Text>
        </div>
        <Select
          label={t("kp.manage.advertisement_service_label")}
          placeholder={t("kp.manage.advertisement_service_none")}
          clearable
          disabled={isPending}
          data={eligibleServices.map((service) => ({
            value: service.id,
            label: service.name,
          }))}
          value={event?.advertisement_service_id ?? null}
          onChange={(value) =>
            setAd({ eventId, data: { service_id: value } })
          }
          nothingFoundMessage={t("kp.manage.advertisement_service_no_eligible")}
        />
      </Stack>
    </Paper>
  );
};

export default DetailsTab;
