import {
  Alert,
  Button,
  Card,
  Center,
  Group,
  Image,
  Loader,
  Stack,
  Table,
  Text,
  Title,
} from "@mantine/core";
import { IconAlertCircle } from "@tabler/icons-react";
import { Link } from "react-router";
import { useTranslation } from "react-i18next";
import { useCurrentUser } from "../context/useCurrentUser";
import BackButton from "../components/BackButton";
import { useGetLatestKp, useListKps } from "../orval/generated/kp/kp";
import { formatKpDisplayDate } from "../schemas/kpSchema";

function formatDate(dateString?: string) {
  return formatKpDisplayDate(dateString);
}

export default function Kp() {
  const { user } = useCurrentUser();
  const { t } = useTranslation();
  const {
    data: latestKp,
    isLoading: isLatestLoading,
    isError: isLatestError,
  } = useGetLatestKp();
  const {
    data: kpEvents,
    isLoading: isListLoading,
    isError: isListError,
  } = useListKps();

  const isLoading = isLatestLoading || isListLoading;

  return (
    <Stack gap="md">
      <BackButton to="/" />
      <Title order={2}>{t("kp.title")}</Title>
      <Text>{t("kp.description")}</Text>

      <Group justify="flex-start" wrap="wrap" mt="xs">
        {user?.is_company && (
          <Button component={Link} to="/kp/join" w="fit-content">
            {t("kp.join_button")}
          </Button>
        )}
        {(user?.is_staff || user?.is_admin) && (
          <Button component={Link} to="/kp/dashboard" w="fit-content">
            {t("kp.dashboard_button")}
          </Button>
        )}
      </Group>

      {isLoading ? (
        <Center py="md">
          <Loader />
        </Center>
      ) : null}

      {(isLatestError || isListError) && !isLoading ? (
        <Alert icon={<IconAlertCircle />} color="red" title={t("server.error")}>
          {t("kp.error")}
        </Alert>
      ) : null}

      {!isLoading && !isLatestError ? (
        <Card withBorder radius="md" p="md">
          <Stack gap="xs">
            <Title order={4}>{t("kp.latest.title")}</Title>
            {latestKp ? (
              <>
                <Text>
                  <Text span fw={600}>
                    {t("kp.latest.name")}:
                  </Text>
                  {latestKp.name}
                </Text>
                <Text>
                  <Text span fw={600}>
                    {t("kp.latest.registration_open")}:
                  </Text>
                  {formatDate(latestKp.registration_open)}
                </Text>
                <Text>
                  <Text span fw={600}>
                    {t("kp.latest.registration_end")}:
                  </Text>
                  {formatDate(latestKp.registration_end)}
                </Text>
                <Text>
                  <Text span fw={600}>
                    {t("kp.latest.finalization_deadline")}:
                  </Text>
                  {formatDate(latestKp.finalization_deadline)}
                </Text>
                <Text>
                  <Text span fw={600}>
                    {t("kp.latest.event_date")}:
                  </Text>
                  {formatDate(latestKp.event_date)}
                </Text>
              </>
            ) : (
              <Text c="dimmed">{t("kp.latest.none")}</Text>
            )}
          </Stack>
        </Card>
      ) : null}

      {!isLoading && !isListError ? (
        <Card withBorder radius="md" p="md">
          <Stack gap="xs">
            <Title order={4}>{t("kp.history.title")}</Title>
            {kpEvents && kpEvents.length > 0 ? (
              <Table striped highlightOnHover withTableBorder>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>{t("kp.history.name")}</Table.Th>
                    <Table.Th>{t("kp.history.registration")}</Table.Th>
                    <Table.Th>{t("kp.history.finalization_deadline")}</Table.Th>
                    <Table.Th>{t("kp.history.event_date")}</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {kpEvents.map((event) => (
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
              <Text c="dimmed">{t("kp.history.none")}</Text>
            )}
          </Stack>
        </Card>
      ) : null}

      <Image
        src="https://placehold.co/1200x600?text=Kontaktparty+Image+Placeholder"
        alt={t("kp.image_alt")}
        radius="md"
      />
    </Stack>
  );
}
