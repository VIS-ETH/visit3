import {
  Badge,
  Button,
  Group,
  Modal,
  Paper,
  Stack,
  Title,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import { IconCopy, IconPlus } from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";
import DataTable, { type DataTableColumn } from "../components/DataTable";
import ErrorAlert from "../components/ErrorAlert";
import {
  emptyKpFormValues,
  toKpWithSettingsRequest,
  type KpWithSettingsFormValues,
} from "../schemas/eventSettingsSchema";
import RecentChanges from "../components/home/RecentChanges";
import CloneKpModal from "../components/kp-manage/CloneKpModal";
import EventFormFields from "../components/kp-manage/EventFormFields";
import { useEventForm } from "../components/kp-manage/use-event-form";
import { useCurrentUser } from "../context/useCurrentUser";
import { useAsyncAction } from "../hooks/use-async-action";
import {
  EVENT_STATUS_COLORS,
  formatKpDateInput,
  getEventStatus,
  type EventStatus,
} from "../utils/kp-utils";
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

const formatTableDate = (dateString?: string) => {
  if (!dateString) return "-";

  const [year, month, day] = dateString.split("-");
  if (!year || !month || !day) return "-";

  return `${day}.${month}.${year}`;
};

const EVENT_STATUS_ORDER: EventStatus[] = [
  "registration_open",
  "upcoming",
  "past",
];

const KpDashboard = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useCurrentUser();
  const isPresident = user?.is_kp_president ?? false;
  const [modalOpened, { open: openModal, close: closeModal }] =
    useDisclosure(false);

  const today = todayAsDateInput();
  const form = useEventForm({
    ...emptyKpFormValues,
    registrationOpen: today,
    registrationEnd: today,
    finalizationDeadline: today,
    nametagsDeadline: today,
    eventDate: today,
  });

  const closeAndReset = () => {
    form.reset();
    closeModal();
  };

  const { data: events, isLoading, isError } = useListKps();
  const [copyModalOpened, { open: openCopyModal, close: closeCopyModal }] =
    useDisclosure(false);
  const latestEvent = events?.reduce<KpEventRow | undefined>(
    (latest, event) =>
      latest && latest.event_date >= event.event_date ? latest : event,
    undefined,
  );
  const statusLabels: Record<EventStatus, string> = {
    upcoming: t("kp.dashboard.status_upcoming"),
    registration_open: t("kp.dashboard.status_registration_open"),
    past: t("kp.dashboard.status_past"),
  };

  const { mutateAsync: createKp } = useCreateKp();
  const { run: createEvent, isRunning: isCreating } = useAsyncAction(
    async (values: KpWithSettingsFormValues) => {
      await createKp({ data: toKpWithSettingsRequest(values) });
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: getListKpsQueryKey() }),
        queryClient.invalidateQueries({ queryKey: getGetLatestKpQueryKey() }),
      ]);
      closeAndReset();
      notifications.show({
        color: "green",
        title: t("kp.dashboard.create_success_title"),
        message: t("kp.dashboard.create_success_message"),
      });
    },
  );

  const columns: DataTableColumn<KpEventRow>[] = [
    {
      key: "name",
      sortValue: (event) => event.name,
      header: t("kp.dashboard.name"),
      render: (event) => event.name,
      searchableValue: (event) => event.name,
    },
    {
      key: "registration-window",
      sortValue: (event) => event.registration_open,
      header: t("kp.dashboard.registration_window"),
      render: (event) =>
        `${formatTableDate(event.registration_open)} - ${formatTableDate(event.registration_end)}`,
      searchableValue: (event) =>
        `${formatTableDate(event.registration_open)} ${formatTableDate(event.registration_end)}`,
    },
    {
      key: "event-date",
      sortValue: (event) => event.event_date,
      header: t("kp.dashboard.event_date"),
      render: (event) => formatTableDate(event.event_date),
      searchableValue: (event) => formatTableDate(event.event_date),
    },
    {
      key: "finalization-deadline",
      sortValue: (event) => event.finalization_deadline,
      header: t("kp.dashboard.finalization_deadline"),
      render: (event) => formatTableDate(event.finalization_deadline),
      searchableValue: (event) => formatTableDate(event.finalization_deadline),
    },
    {
      key: "nametags-deadline",
      sortValue: (event) => event.nametags_deadline,
      header: t("kp.dashboard.nametags_deadline"),
      render: (event) => formatTableDate(event.nametags_deadline),
      searchableValue: (event) => formatTableDate(event.nametags_deadline),
    },
    {
      key: "status",
      sortValue: (event) => EVENT_STATUS_ORDER.indexOf(getEventStatus(event)),
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
  ];

  return (
    <Stack gap="md">
      <RecentChanges />
      <Group justify="space-between" align="center">
        <Title order={2}>{t("kp.dashboard.title")}</Title>
        {isPresident ? (
          <Group gap="sm">
            <Button
              variant="default"
              leftSection={<IconCopy size={16} />}
              disabled={!latestEvent}
              onClick={openCopyModal}
            >
              {t("kp.dashboard.copy_button")}
            </Button>
            <Button leftSection={<IconPlus size={16} />} onClick={openModal}>
              {t("kp.dashboard.create_new_button")}
            </Button>
          </Group>
        ) : null}
      </Group>

      {isPresident && latestEvent ? (
        <CloneKpModal
          eventId={latestEvent.id}
          sourceEvents={events}
          opened={copyModalOpened}
          onClose={closeCopyModal}
        />
      ) : null}

      <Modal
        opened={modalOpened}
        onClose={isCreating ? () => undefined : closeAndReset}
        title={t("kp.dashboard.create_title")}
        size="lg"
        centered
      >
        <form onSubmit={form.onSubmit((values) => void createEvent(values))}>
          <Stack gap="sm">
            <EventFormFields form={form} disabled={isCreating} />
            <Group justify="flex-end">
              <Button
                variant="default"
                onClick={closeAndReset}
                disabled={isCreating}
              >
                {t("common.cancel")}
              </Button>
              <Button
                type="submit"
                loading={isCreating}
                disabled={!form.isValid()}
              >
                {t("kp.dashboard.create_button")}
              </Button>
            </Group>
          </Stack>
        </form>
      </Modal>

      {isError ? <ErrorAlert>{t("kp.dashboard.error")}</ErrorAlert> : null}

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
