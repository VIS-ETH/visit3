import { Alert, Card, Center, Loader, Stack, Text, Title } from "@mantine/core";
import { IconAlertCircle } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import BackButton from "../components/BackButton";
import { useGetLatestKp } from "../orval/generated/kp/kp";
import { formatKpDisplayDate } from "../schemas/kpSchema";

function formatDate(dateString?: string) {
  return formatKpDisplayDate(dateString);
}

export default function KpJoin() {
  const { t } = useTranslation();

  const { data: latestKp, isLoading, isError } = useGetLatestKp();

  return (
    <Stack gap="md">
      <BackButton to="/kp" />
      <Title order={2}>{t("kp.join.title")}</Title>
      <Text>{t("kp.join.description")}</Text>

      {isLoading ? (
        <Center py="md">
          <Loader />
        </Center>
      ) : null}

      {isError && !isLoading ? (
        <Alert icon={<IconAlertCircle />} color="red" title={t("server.error")}>
          {t("kp.join.error")}
        </Alert>
      ) : null}

      {!isLoading && !isError ? (
        <Card withBorder radius="md" p="md">
          <Stack gap="sm">
            <Title order={4}>{t("kp.join.current_event")}</Title>
            {latestKp ? (
              <>
                <Text>
                  <Text span fw={600}>
                    {t("kp.join.name")}:
                  </Text>
                  {latestKp.name}
                </Text>
                <Text>
                  <Text span fw={600}>
                    {t("kp.join.registration_window")}:
                  </Text>
                  {formatDate(latestKp.registration_open)} -{" "}
                  {formatDate(latestKp.registration_end)}
                </Text>
                <Text>
                  <Text span fw={600}>
                    {t("kp.join.finalization_deadline")}:
                  </Text>
                  {formatDate(latestKp.finalization_deadline)}
                </Text>
                <Text>
                  <Text span fw={600}>
                    {t("kp.join.nametags_deadline")}:
                  </Text>
                  {formatDate(latestKp.nametags_deadline)}
                </Text>
                <Text>
                  <Text span fw={600}>
                    {t("kp.join.event_date")}:
                  </Text>
                  {formatDate(latestKp.event_date)}
                </Text>
              </>
            ) : (
              <Text c="dimmed">{t("kp.join.no_event")}</Text>
            )}
          </Stack>
        </Card>
      ) : null}
    </Stack>
  );
}
