import {
  Alert,
  Button,
  Card,
  Center,
  Group,
  Loader,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconAlertCircle } from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import BackButton from "../components/BackButton";
import {
  getGetLatestKpQueryKey,
  getListKpsQueryKey,
  useCreateKp,
  useGetCompaniesForKp,
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
  const [year, setYear] = useState<string>(String(new Date().getFullYear()));
  const [registrationOpen, setRegistrationOpen] =
    useState<string>(todayAsDateInput());
  const [registrationEnd, setRegistrationEnd] =
    useState<string>(todayAsDateInput());
  const [eventDate, setEventDate] = useState<string>(todayAsDateInput());
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);

  const {
    data: events,
    isLoading: isEventsLoading,
    isError: isEventsError,
  } = useListKps();

  const {
    data: companies,
    isLoading: isCompaniesLoading,
    isError: isCompaniesError,
  } = useGetCompaniesForKp(selectedEventId ?? "", {
    query: { enabled: !!selectedEventId },
  });

  const eventOptions = useMemo(
    () =>
      (events ?? []).map((event) => ({
        value: event.id ?? "",
        label: `${event.year} (${formatDate(event.event_date)})`,
      })),
    [events],
  );

  const { mutate: createEvent, isPending: isCreating } = useCreateKp({
    mutation: {
      onSuccess: async (newEvent) => {
        await queryClient.invalidateQueries({ queryKey: getListKpsQueryKey() });
        await queryClient.invalidateQueries({
          queryKey: getGetLatestKpQueryKey(),
        });

        if (newEvent.id) {
          setSelectedEventId(newEvent.id);
        }

        notifications.show({
          color: "green",
          title: t("kp.dashboard.create_success_title"),
          message: t("kp.dashboard.create_success_message"),
        });
      },
    },
  });

  const handleCreate = () => {
    const parsedYear = Number.parseInt(year, 10);
    if (!Number.isFinite(parsedYear)) {
      notifications.show({
        color: "red",
        title: t("server.error"),
        message: t("kp.dashboard.invalid_year"),
      });
      return;
    }

    createEvent({
      data: {
        year: parsedYear,
        registration_open: registrationOpen,
        registration_end: registrationEnd,
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
              label={t("kp.dashboard.year")}
              value={year}
              onChange={(event) => setYear(event.currentTarget.value)}
              placeholder="2026"
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

      {isEventsLoading ? (
        <Center py="md">
          <Loader />
        </Center>
      ) : null}

      {isEventsError ? (
        <Alert icon={<IconAlertCircle />} color="red" title={t("server.error")}>
          {t("kp.dashboard.error")}
        </Alert>
      ) : null}

      {!isEventsLoading && !isEventsError ? (
        <Card withBorder radius="md" p="md">
          <Stack gap="sm">
            <Title order={4}>{t("kp.dashboard.list_title")}</Title>
            {events && events.length > 0 ? (
              <Table striped highlightOnHover withTableBorder>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>{t("kp.dashboard.year")}</Table.Th>
                    <Table.Th>{t("kp.dashboard.registration_window")}</Table.Th>
                    <Table.Th>{t("kp.dashboard.event_date")}</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {events.map((event) => (
                    <Table.Tr
                      key={event.id ?? `${event.year}-${event.event_date}`}
                    >
                      <Table.Td>{event.year}</Table.Td>
                      <Table.Td>
                        {formatDate(event.registration_open)} -{" "}
                        {formatDate(event.registration_end)}
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

      <Card withBorder radius="md" p="md">
        <Stack gap="sm">
          <Title order={4}>{t("kp.dashboard.companies_title")}</Title>
          <Select
            label={t("kp.dashboard.choose_event")}
            data={eventOptions.filter((option) => option.value.length > 0)}
            value={selectedEventId}
            onChange={setSelectedEventId}
            placeholder={t("kp.dashboard.choose_event_placeholder")}
            searchable
          />

          {isCompaniesLoading ? (
            <Center py="sm">
              <Loader size="sm" />
            </Center>
          ) : null}

          {isCompaniesError ? (
            <Alert
              icon={<IconAlertCircle />}
              color="red"
              title={t("server.error")}
            >
              {t("kp.dashboard.companies_error")}
            </Alert>
          ) : null}

          {!isCompaniesLoading && !isCompaniesError && selectedEventId ? (
            companies && companies.length > 0 ? (
              <Table striped highlightOnHover withTableBorder>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>{t("kp.dashboard.company_name")}</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {companies.map((company) => (
                    <Table.Tr key={company.id ?? company.name}>
                      <Table.Td>{company.name}</Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            ) : (
              <Text c="dimmed">{t("kp.dashboard.no_companies")}</Text>
            )
          ) : null}
        </Stack>
      </Card>
    </Stack>
  );
}
