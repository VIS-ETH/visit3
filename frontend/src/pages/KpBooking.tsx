import { Group, Stack, Text, Title } from "@mantine/core";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router";
import BackButton from "../components/BackButton";
import ErrorAlert from "../components/ErrorAlert";
import PageLoader from "../components/PageLoader";
import { useGetKpById } from "../orval/generated/kp/kp";
import KpBookingStepper from "../components/exhibitor-booking/KpBookingStepper";

const KpBooking = () => {
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

  if (isLoading) return <PageLoader />;

  if (!eventId || isError || !event) {
    return (
      <Stack gap="md">
        <BackButton to={eventId ? `/kp/${eventId}` : "/kp"} />
        <ErrorAlert>{t("kp.booking.error")}</ErrorAlert>
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
};
export default KpBooking;
