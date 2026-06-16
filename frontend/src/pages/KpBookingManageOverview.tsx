import {
  Alert,
  Badge,
  Button,
  Card,
  Center,
  Group,
  Loader,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import {
  IconAlertCircle,
  IconBuildingStore,
  IconChevronRight,
  IconListDetails,
} from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router";
import BackButton from "../components/BackButton";
import { KpBookingRecap } from "../components/KpBookingRecap";
import { useGetKpById, useGetMyBooking } from "../orval/generated/kp/kp";

const KpBookingManageOverview = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { id = "", bookingId = "" } = useParams<{
    id: string;
    bookingId: string;
  }>();
  const eventId = id.trim();
  const normalizedBookingId = bookingId.trim();
  const {
    data: event,
    isLoading: isLoadingEvent,
    isError: isEventError,
  } = useGetKpById(eventId, {
    query: { enabled: Boolean(eventId) },
  });
  const {
    data: booking,
    isLoading: isLoadingBooking,
    isFetching: isFetchingBooking,
    isError: isBookingError,
  } = useGetMyBooking(eventId, {
    query: { enabled: Boolean(eventId) },
  });

  if (isLoadingEvent || isLoadingBooking || isFetchingBooking) {
    return (
      <Center py="xl">
        <Loader />
      </Center>
    );
  }

  if (
    !eventId ||
    !normalizedBookingId ||
    isEventError ||
    isBookingError ||
    !event ||
    booking?.id !== normalizedBookingId
  ) {
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
    <Stack gap="md">
      <BackButton to={`/kp/${eventId}`} />
      <div>
        <Title order={2}>
          {t("kp.booking_manage.title", {
            bookingNumber: booking.booking_number,
          })}
        </Title>
        <Text c="dimmed" size="sm">
          {event.name}
        </Text>
      </div>

      <KpBookingRecap booking={booking} />

      <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
        <Card withBorder radius="md" p="lg">
          <Stack gap="sm">
            <Group justify="space-between" align="flex-start">
              <IconBuildingStore size={22} />
              <Badge
                color={booking.company_details ? "green" : "gray"}
                variant="light"
              >
                {booking.company_details
                  ? t("kp.manage.booking_details_submitted")
                  : t("kp.manage.booking_details_missing")}
              </Badge>
            </Group>
            <div>
              <Title order={4}>{t("kp.booking_manage.booklet_details_page_title")}</Title>
              <Text c="dimmed" size="sm">
                {t("kp.booking_manage.booklet_details_page_description")}
              </Text>
            </div>
            <Button
              variant="light"
              onClick={() =>
                navigate(
                  `/kp/${eventId}/booking/${booking.id}/manage/booklet-details`,
                )
              }
            >
              {t("kp.booking_manage.manage_booklet_details")}
            </Button>
          </Stack>
        </Card>

        <Card withBorder radius="md" p="lg">
          <Stack gap="sm">
            <Group justify="space-between" align="flex-start">
              <IconListDetails size={22} />
              <IconChevronRight size={18} />
            </Group>
            <div>
              <Title order={4}>{t("kp.booking_manage.services_page_title")}</Title>
              <Text c="dimmed" size="sm">
                {t("kp.booking_manage.services_page_description")}
              </Text>
            </div>
            <Button
              variant="light"
              onClick={() =>
                navigate(`/kp/${eventId}/booking/${booking.id}/manage/services`)
              }
            >
              {t("kp.booking_manage.manage_services")}
            </Button>
          </Stack>
        </Card>

        <Card withBorder radius="md" p="lg">
          <Stack gap="sm">
            <Group justify="space-between" align="flex-start">
              <IconListDetails size={22} />
              <IconChevronRight size={18} />
            </Group>
            <div>
              <Title order={4}>{t("kp.booking_manage.summary_page_title")}</Title>
              <Text c="dimmed" size="sm">
                {t("kp.booking_manage.summary_page_description")}
              </Text>
            </div>
            <Button
              variant="light"
              onClick={() => navigate(`/kp/${eventId}/booking/${booking.id}`)}
            >
              {t("kp.booking_manage.view_summary")}
            </Button>
          </Stack>
        </Card>
      </SimpleGrid>
    </Stack>
  );
};

export default KpBookingManageOverview;
