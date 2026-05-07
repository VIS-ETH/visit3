import {
  Alert,
  Badge,
  Button,
  Card,
  Center,
  Group,
  Loader,
  Modal,
  Stack,
  Table,
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
import { kpSchema, type KpFormValues } from "../schemas/kpSchema";
import {
  EVENT_STATUS_COLORS,
  formatKpDateInput,
  formatKpDisplayDate,
  getEventStatus,
  toKpIsoDate,
  type EventStatus,
} from "../utils/kp-utils";
import { useTranslatedForm } from "../utils/translator";
import {
  getGetLatestKpQueryKey,
  getListKpsQueryKey,
  useCreateKp,
  useListKps,
} from "../orval/generated/kp/kp";

function todayAsDateInput() {
  return formatKpDateInput(new Date());
}

const dateFieldNames = [
  "registrationOpen",
  "registrationEnd",
  "finalizationDeadline",
  "nametagsDeadline",
  "eventDate",
] as const;

export default function KpDashboard() {
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
                placeholder="Kontaktparty 2026"
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

      {isLoading ? (
        <Center py="xl">
          <Loader />
        </Center>
      ) : null}

      {isError ? (
        <Alert icon={<IconAlertCircle />} color="red" title={t("server.error")}>
          {t("kp.dashboard.error")}
        </Alert>
      ) : null}

      {!isLoading && !isError ? (
        <Card withBorder radius="md" p={0}>
          {events && events.length > 0 ? (
            <Table highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>{t("kp.dashboard.name")}</Table.Th>
                  <Table.Th>{t("kp.dashboard.registration_window")}</Table.Th>
                  <Table.Th>{t("kp.dashboard.event_date")}</Table.Th>
                  <Table.Th>{t("kp.dashboard.finalization_deadline")}</Table.Th>
                  <Table.Th>{t("kp.dashboard.nametags_deadline")}</Table.Th>
                  <Table.Th>Status</Table.Th>
                  <Table.Th />
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {events.map((event) => {
                  const status = getEventStatus(event);
                  return (
                    <Table.Tr
                      key={event.id ?? `${event.name}-${event.event_date}`}
                    >
                      <Table.Td fw={500}>{event.name}</Table.Td>
                      <Table.Td>
                        {formatKpDisplayDate(event.registration_open)} -{" "}
                        {formatKpDisplayDate(event.registration_end)}
                      </Table.Td>
                      <Table.Td>
                        {formatKpDisplayDate(event.event_date)}
                      </Table.Td>
                      <Table.Td>
                        {formatKpDisplayDate(event.finalization_deadline)}
                      </Table.Td>
                      <Table.Td>
                        {formatKpDisplayDate(event.nametags_deadline)}
                      </Table.Td>
                      <Table.Td>
                        <Badge
                          color={EVENT_STATUS_COLORS[status]}
                          variant="light"
                          size="sm"
                        >
                          {statusLabels[status]}
                        </Badge>
                      </Table.Td>
                      <Table.Td>
                        <Button
                          size="xs"
                          variant="light"
                          component={Link}
                          to={`/kp/${event.id}`}
                        >
                          {t("kp.dashboard.manage_button")}
                        </Button>
                      </Table.Td>
                    </Table.Tr>
                  );
                })}
              </Table.Tbody>
            </Table>
          ) : (
            <Text c="dimmed" p="md">
              {t("kp.dashboard.no_events")}
            </Text>
          )}
        </Card>
      ) : null}
    </Stack>
  );
}
