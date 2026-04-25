import {
  Alert,
  Button,
  Card,
  Center,
  Group,
  Loader,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconAlertCircle } from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import BackButton from "../components/BackButton";
import {
  getGetLatestKpQueryKey,
  getListKpsQueryKey,
  useCreateKp,
  useListKps,
} from "../orval/generated/kp/kp";

function formatDate(dateString?: string) {
  if (!dateString) return "-";
  return new Date(dateString).toLocaleDateString();
}

function todayAsDateInput() {
  return new Date().toISOString().slice(0, 10);
}

export default function KpDashboard() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [name, setName] = useState<string>("");
  const [registrationOpen, setRegistrationOpen] =
    useState<string>(todayAsDateInput());
  const [registrationEnd, setRegistrationEnd] =
    useState<string>(todayAsDateInput());
  const [finalizationDeadline, setFinalizationDeadline] =
    useState<string>(todayAsDateInput());
  const [eventDate, setEventDate] = useState<string>(todayAsDateInput());

  const { data: events, isLoading, isError } = useListKps();

  const { mutate: createEvent, isPending: isCreating } = useCreateKp({
    mutation: {
      onSuccess: async () => {
        await queryClient.invalidateQueries({ queryKey: getListKpsQueryKey() });
        await queryClient.invalidateQueries({
          queryKey: getGetLatestKpQueryKey(),
        });
        setName("");

        notifications.show({
          color: "green",
          title: t("kp.dashboard.create_success_title"),
          message: t("kp.dashboard.create_success_message"),
        });
      },
    },
  });

  const handleCreate = () => {
    if (!name.trim()) {
      notifications.show({
        color: "red",
        title: t("server.error"),
        message: t("kp.dashboard.invalid_name"),
      });
      return;
    }

    createEvent({
      data: {
        name: name.trim(),
        registration_open: registrationOpen,
        registration_end: registrationEnd,
        finalization_deadline: finalizationDeadline,
        event_date: eventDate,
      },
    });
  };

  return (
    <Stack gap="md">
      <BackButton to="/kp" />
      <Title order={2}>{t("kp.dashboard.title")}</Title>
      <Text>{t("kp.dashboard.description")}</Text>

      <Card withBorder radius="md" p="md">
        <Stack gap="sm">
          <Title order={4}>{t("kp.dashboard.create_title")}</Title>
          <Group grow>
            <TextInput
              label={t("kp.dashboard.name")}
              value={name}
              onChange={(event) => setName(event.currentTarget.value)}
              placeholder="Kontaktparty 2026"
            />
            <TextInput
              type="date"
              label={t("kp.dashboard.registration_open")}
              value={registrationOpen}
              onChange={(event) =>
                setRegistrationOpen(event.currentTarget.value)
              }
            />
          </Group>
          <Group grow>
            <TextInput
              type="date"
              label={t("kp.dashboard.registration_end")}
              value={registrationEnd}
              onChange={(event) =>
                setRegistrationEnd(event.currentTarget.value)
              }
            />
            <TextInput
              type="date"
              label={t("kp.dashboard.finalization_deadline")}
              value={finalizationDeadline}
              onChange={(event) =>
                setFinalizationDeadline(event.currentTarget.value)
              }
            />
          </Group>
          <Group grow>
            <TextInput
              type="date"
              label={t("kp.dashboard.event_date")}
              value={eventDate}
              onChange={(event) => setEventDate(event.currentTarget.value)}
            />
          </Group>
          <Group justify="flex-end">
            <Button onClick={handleCreate} loading={isCreating}>
              {t("kp.dashboard.create_button")}
            </Button>
          </Group>
        </Stack>
      </Card>

      {isLoading ? (
        <Center py="md">
          <Loader />
        </Center>
      ) : null}

      {isError ? (
        <Alert icon={<IconAlertCircle />} color="red" title={t("server.error")}>
          {t("kp.dashboard.error")}
        </Alert>
      ) : null}

      {!isLoading && !isError ? (
        <Card withBorder radius="md" p="md">
          <Stack gap="sm">
            <Title order={4}>{t("kp.dashboard.list_title")}</Title>
            {events && events.length > 0 ? (
              <Table striped highlightOnHover withTableBorder>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>{t("kp.dashboard.name")}</Table.Th>
                    <Table.Th>{t("kp.dashboard.registration_window")}</Table.Th>
                    <Table.Th>
                      {t("kp.dashboard.finalization_deadline")}
                    </Table.Th>
                    <Table.Th>{t("kp.dashboard.event_date")}</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {events.map((event) => (
                    <Table.Tr
                      key={event.id ?? `${event.name}-${event.event_date}`}
                    >
                      <Table.Td>{event.name}</Table.Td>
                      <Table.Td>
                        {formatDate(event.registration_open)} -{" "}
                        {formatDate(event.registration_end)}
                      </Table.Td>
                      <Table.Td>
                        {formatDate(event.finalization_deadline)}
                      </Table.Td>
                      <Table.Td>{formatDate(event.event_date)}</Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            ) : (
              <Text c="dimmed">{t("kp.dashboard.no_events")}</Text>
            )}
          </Stack>
        </Card>
      ) : null}
    </Stack>
  );
}
