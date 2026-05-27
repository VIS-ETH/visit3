import {
  Alert,
  Badge,
  Button,
  Group,
  Modal,
  Paper,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import { IconAlertCircle, IconPlus } from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import type { ChangeEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import BackButton from "../components/BackButton";
import DataTable, { type DataTableColumn } from "../components/DataTable";
import { kpSchema, toKpRequest, type KpFormValues } from "../schemas/kpSchema";
import {
  EVENT_STATUS_COLORS,
  formatKpDateInput,
  formatKpDisplayDate,
  getEventStatus,
  type EventStatus,
} from "../utils/kp-utils";
import { useTranslatedForm } from "../utils/translator";
import {
  getGetLatestKpQueryKey,
  getListKpsQueryKey,
  type ListKpsQueryResult,
  useCreateKp,
  useListKps,
} from "../orval/generated/kp/kp";

type KpEventRow = ListKpsQueryResult[number];

const todayAsDateInput = () => {
  return formatKpDateInput(new Date());
};

const dateFieldNames = [
  "registrationOpen",
  "registrationEnd",
  "finalizationDeadline",
  "nametagsDeadline",
  "eventDate",
] as const;

const KpDashboard = () => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [modalOpened, { open: openModal, close: closeModal }] =
    useDisclosure(false);

  const initialValues: KpFormValues = {
    name: "",
    registrationOpen: todayAsDateInput(),
    registrationEnd: todayAsDateInput(),
    finalizationDeadline: todayAsDateInput(),
    nametagsDeadline: todayAsDateInput(),
    eventDate: todayAsDateInput(),
  };
  const form = useTranslatedForm<typeof kpSchema>(kpSchema, {
    initialValues,
    validateInputOnChange: true,
  });

  const getDateInputProps = (field: (typeof dateFieldNames)[number]) => {
    const inputProps = form.getInputProps(field);

    return {
      ...inputProps,
      onChange: (event: ChangeEvent<HTMLInputElement>) => {
        inputProps.onChange(event);
        for (const fieldName of dateFieldNames) {
          form.validateField(fieldName);
        }
      },
    };
  };

  const { data: events, isLoading, isError } = useListKps();
  const statusLabels: Record<EventStatus, string> = {
    upcoming: t("kp.dashboard.status_upcoming"),
    registration_open: t("kp.dashboard.status_registration_open"),
    past: t("kp.dashboard.status_past"),
  };

  const { mutate: createEvent, isPending: isCreating } = useCreateKp({
    mutation: {
      onSuccess: async () => {
        await queryClient.invalidateQueries({ queryKey: getListKpsQueryKey() });
        await queryClient.invalidateQueries({
          queryKey: getGetLatestKpQueryKey(),
        });
        form.reset();
        closeModal();

        notifications.show({
          color: "green",
          title: t("kp.dashboard.create_success_title"),
          message: t("kp.dashboard.create_success_message"),
        });
      },
    },
  });

  const handleCreate = (values: KpFormValues) => {
    createEvent({
      data: toKpRequest(values),
    });
  };

  const columns: DataTableColumn<KpEventRow>[] = [
    {
      key: "name",
      header: t("kp.dashboard.name"),
      render: (event) => event.name,
      searchableValue: (event) => event.name,
    },
    {
      key: "registration-window",
      header: t("kp.dashboard.registration_window"),
      render: (event) =>
        `${formatKpDisplayDate(event.registration_open)} - ${formatKpDisplayDate(event.registration_end)}`,
      searchableValue: (event) =>
        `${formatKpDisplayDate(event.registration_open)} ${formatKpDisplayDate(event.registration_end)}`,
    },
    {
      key: "event-date",
      header: t("kp.dashboard.event_date"),
      render: (event) => formatKpDisplayDate(event.event_date),
      searchableValue: (event) => formatKpDisplayDate(event.event_date),
    },
    {
      key: "finalization-deadline",
      header: t("kp.dashboard.finalization_deadline"),
      render: (event) => formatKpDisplayDate(event.finalization_deadline),
      searchableValue: (event) =>
        formatKpDisplayDate(event.finalization_deadline),
    },
    {
      key: "nametags-deadline",
      header: t("kp.dashboard.nametags_deadline"),
      render: (event) => formatKpDisplayDate(event.nametags_deadline),
      searchableValue: (event) => formatKpDisplayDate(event.nametags_deadline),
    },
    {
      key: "status",
      header: t("kp.dashboard.status_label"),
      render: (event) => {
        const status = getEventStatus(event);
        return (
          <Badge color={EVENT_STATUS_COLORS[status]} variant="light" size="sm">
            {statusLabels[status]}
          </Badge>
        );
      },
      searchableValue: (event) => statusLabels[getEventStatus(event)],
    },
    {
      key: "actions",
      header: "",
      render: (event) => (
        <Button
          size="xs"
          variant="light"
          component={Link}
          to={`/kp/${event.id}`}
        >
          {t("kp.dashboard.manage_button")}
        </Button>
      ),
      width: 90,
    },
  ];

  return (
    <Stack gap="md">
      <BackButton to="/" />

      <Group justify="space-between" align="center">
        <div>
          <Title order={2}>{t("kp.dashboard.title")}</Title>
          <Text c="dimmed" size="sm">
            {t("kp.dashboard.description")}
          </Text>
        </div>
        <Button leftSection={<IconPlus size={16} />} onClick={openModal}>
          {t("kp.dashboard.create_new_button")}
        </Button>
      </Group>

      <Modal
        opened={modalOpened}
        onClose={closeModal}
        title={t("kp.dashboard.create_title")}
        size="lg"
        centered
      >
        <form onSubmit={form.onSubmit(handleCreate)}>
          <Stack gap="sm">
            <Group grow>
              <TextInput
                label={t("kp.dashboard.name")}
                placeholder={t("kp.dashboard.name_input_placeholder")}
                disabled={isCreating}
                {...form.getInputProps("name")}
              />
              <TextInput
                label={t("kp.dashboard.registration_open")}
                placeholder={t("kp.dashboard.date_input_placeholder")}
                description={t("kp.dashboard.date_input_hint")}
                disabled={isCreating}
                {...getDateInputProps("registrationOpen")}
              />
            </Group>
            <Group grow>
              <TextInput
                label={t("kp.dashboard.registration_end")}
                placeholder={t("kp.dashboard.date_input_placeholder")}
                description={t("kp.dashboard.date_input_hint")}
                disabled={isCreating}
                {...getDateInputProps("registrationEnd")}
              />
              <TextInput
                label={t("kp.dashboard.finalization_deadline")}
                placeholder={t("kp.dashboard.date_input_placeholder")}
                description={t("kp.dashboard.date_input_hint")}
                disabled={isCreating}
                {...getDateInputProps("finalizationDeadline")}
              />
            </Group>
            <Group grow>
              <TextInput
                label={t("kp.dashboard.nametags_deadline")}
                placeholder={t("kp.dashboard.date_input_placeholder")}
                description={t("kp.dashboard.date_input_hint")}
                disabled={isCreating}
                {...getDateInputProps("nametagsDeadline")}
              />
              <TextInput
                label={t("kp.dashboard.event_date")}
                placeholder={t("kp.dashboard.date_input_placeholder")}
                description={t("kp.dashboard.date_input_hint")}
                disabled={isCreating}
                {...getDateInputProps("eventDate")}
              />
            </Group>
            <Group justify="flex-end">
              <Button
                variant="default"
                onClick={closeModal}
                disabled={isCreating}
              >
                {t("common.cancel")}
              </Button>
              <Button
                type="submit"
                loading={isCreating}
                disabled={isCreating || !form.isValid()}
              >
                {t("kp.dashboard.create_button")}
              </Button>
            </Group>
          </Stack>
        </form>
      </Modal>

      {isError ? (
        <Alert icon={<IconAlertCircle />} color="red" title={t("server.error")}>
          {t("kp.dashboard.error")}
        </Alert>
      ) : null}

      {!isError ? (
        <Paper withBorder p="lg" radius="md">
          <DataTable
            columns={columns}
            data={events}
            emptyLabel={t("kp.dashboard.no_events")}
            getRowKey={(event) => event.id}
            isLoading={isLoading}
            onRowClick={(event) => navigate(`/kp/${event.id}`)}
          />
        </Paper>
      ) : null}
    </Stack>
  );
};
export default KpDashboard;
