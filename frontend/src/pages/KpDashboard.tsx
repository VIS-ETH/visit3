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
import type { ChangeEvent } from "react";
import { useTranslation } from "react-i18next";
import BackButton from "../components/BackButton";
import {
  formatKpDateInput,
  formatKpDisplayDate,
  kpSchema,
  toKpIsoDate,
  type KpFormValues,
} from "../schemas/kpSchema";
import { useTranslatedForm } from "../utils/translator";
import {
  getGetLatestKpQueryKey,
  getListKpsQueryKey,
  useCreateKp,
  useListKps,
} from "../orval/generated/kp/kp";

function formatDate(dateString?: string) {
  return formatKpDisplayDate(dateString);
}

function todayAsDateInput() {
  return formatKpDateInput(new Date());
}

const dateFieldNames = [
  "registrationOpen",
  "registrationEnd",
  "finalizationDeadline",
  "eventDate",
] as const;

export default function KpDashboard() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const initialValues: KpFormValues = {
    name: "",
    registrationOpen: todayAsDateInput(),
    registrationEnd: todayAsDateInput(),
    finalizationDeadline: todayAsDateInput(),
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

  const { mutate: createEvent, isPending: isCreating } = useCreateKp({
    mutation: {
      onSuccess: async () => {
        await queryClient.invalidateQueries({ queryKey: getListKpsQueryKey() });
        await queryClient.invalidateQueries({
          queryKey: getGetLatestKpQueryKey(),
        });
        form.reset();

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
        event_date: toKpIsoDate(values.eventDate),
      },
    });
  };

  return (
    <Stack gap="md">
      <BackButton to="/kp" />
      <Title order={2}>{t("kp.dashboard.title")}</Title>
      <Text>{t("kp.dashboard.description")}</Text>

      <Card withBorder radius="md" p="md">
        <form onSubmit={form.onSubmit(handleCreate)}>
          <Stack gap="sm">
            <Title order={4}>{t("kp.dashboard.create_title")}</Title>
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
                label={t("kp.dashboard.event_date")}
                placeholder={t("kp.dashboard.date_input_placeholder")}
                description={t("kp.dashboard.date_input_hint")}
                disabled={isCreating}
                {...getDateInputProps("eventDate")}
              />
            </Group>
            <Group justify="flex-end">
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
