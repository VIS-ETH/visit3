import {
  Alert,
  Center,
  Group,
  Loader,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { IconAlertCircle } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router";
import BackButton from "../components/BackButton";
import { useGetKpById } from "../orval/generated/kp/kp";
import KpBookingStepper from "./KpBookingStepper.tsx";

export default function KpBooking() {
  const { t } = useTranslation();
  const { id = "" } = useParams<{ id: string }>();
  const eventId = id.trim();
  const {
    data: event,
    isLoading,
    isError,
  } = useGetKpById(eventId, {
    query: { enabled: Boolean(eventId) },
  });

  if (isLoading) {
    return (
      <Center py="xl">
        <Loader />
      </Center>
    );
  }

  if (!eventId || isError || !event) {
    return (
      <Stack gap="md">
        <BackButton to={eventId ? `/kp/${eventId}` : "/kp"} />
        <Alert icon={<IconAlertCircle />} color="red" title={t("server.error")}>
          {t("kp.booking.error")}
        </Alert>
      </Stack>
    );
  }

  return (
    <Stack gap="sm">
      <Group justify="space-between" align="center">
        <div>
          <Title order={2}>{t("kp.booking.title")}</Title>
          <Text c="dimmed" size="sm">
            {event.name}
          </Text>
        </div>
      </Group>

      <KpBookingStepper event={event} />
    </Stack>
  );
}
