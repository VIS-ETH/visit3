import {
  Alert,
  Badge,
  Button,
  Center,
  Group,
  Loader,
  Paper,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconAlertCircle } from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router";
import BackButton from "../components/BackButton";
import { KpBookingStatusBadge } from "../components/KpBookingStatusBadge";
import { KpBookingStatus } from "../orval/generated/fastAPI.schemas";
import {
  getGetEventBookingQueryKey,
  getListEventBookingsQueryKey,
  useConfirmBooking,
  useGetEventBooking,
} from "../orval/generated/kp/kp";
import { formatPrice } from "../utils/price-utils";

const DetailField = ({ label, value }: { label: string; value: ReactNode }) => (
  <Stack gap={2}>
    <Text c="dimmed" size="sm">
      {label}
    </Text>
    {typeof value === "string" || typeof value === "number" ? (
      <Text fw={500}>{value}</Text>
    ) : (
      value
    )}
  </Stack>
);

const KpBookingDetails = () => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { id, bookingId } = useParams<{ id: string; bookingId: string }>();
  const backToBookings = id ? `/kp/${id}?tab=bookings` : "/kp";
  const {
    data: booking,
    isError,
    isLoading,
  } = useGetEventBooking(id ?? "", bookingId ?? "", {
    query: { enabled: Boolean(id && bookingId) },
  });
  const { mutate: confirmBooking, isPending: isConfirming } = useConfirmBooking(
    {
      mutation: {
        onSuccess: async () => {
          await Promise.all([
            queryClient.invalidateQueries({
              queryKey: getGetEventBookingQueryKey(id, bookingId),
            }),
            queryClient.invalidateQueries({
              queryKey: getListEventBookingsQueryKey(id),
            }),
          ]);
          notifications.show({
            color: "green",
            message: t("kp.manage.booking_confirmed"),
          });
        },
      },
    },
  );

  const canConfirm = booking?.status === KpBookingStatus.FINALIZED;

  const handleConfirmBooking = () => {
    if (!bookingId || !confirm(t("kp.manage.booking_confirm_prompt"))) return;
    confirmBooking({ bookingId });
  };

  if (!id || !bookingId) {
    return (
      <Stack gap="md">
        <BackButton to="/kp" />
        <Alert icon={<IconAlertCircle />} color="red">
          {t("kp.manage.booking_detail_not_found")}
        </Alert>
      </Stack>
    );
  }

  if (isLoading) {
    return (
      <Stack gap="md">
        <BackButton to={backToBookings} />
        <Center py="xl">
          <Loader />
        </Center>
      </Stack>
    );
  }

  if (isError || !booking) {
    return (
      <Stack gap="md">
        <BackButton to={backToBookings} />
        <Alert icon={<IconAlertCircle />} color="red">
          {t("kp.manage.booking_detail_not_found")}
        </Alert>
      </Stack>
    );
  }

  return (
    <Stack gap="md">
      <BackButton to={backToBookings} />

      <Group justify="space-between" align="flex-start">
        <div>
          <Title order={2}>
            {t("kp.manage.booking_detail_title", {
              bookingNumber: booking.booking_number,
            })}
          </Title>
          <Text c="dimmed" size="sm">
            {booking.company.name}
          </Text>
        </div>
        <Group gap="sm">
          <KpBookingStatusBadge status={booking.status} />
          {canConfirm ? (
            <Button
              color="green"
              loading={isConfirming}
              onClick={handleConfirmBooking}
            >
              {t("kp.manage.booking_confirm")}
            </Button>
          ) : null}
        </Group>
      </Group>

      <Paper withBorder p="lg" radius="md">
        <Stack gap="lg">
          <Title order={4}>{t("kp.manage.booking_detail_overview")}</Title>
          <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} spacing="lg">
            <DetailField
              label={t("kp.manage.booking_company")}
              value={booking.company.name}
            />
            <DetailField
              label={t("kp.manage.booking_booth_zone")}
              value={booking.booth_zone.name}
            />
            <DetailField
              label={t("kp.manage.booking_booth_nr")}
              value={booking.booth_nr ?? "-"}
            />
            <DetailField
              label={t("kp.manage.booking_total")}
              value={`CHF ${formatPrice(booking.total_price)}`}
            />
            <DetailField
              label={t("kp.manage.booking_nametags")}
              value={booking.nametag_count}
            />
            <DetailField
              label={t("kp.manage.booking_waitlist")}
              value={booking.waitlist_count}
            />
          </SimpleGrid>
        </Stack>
      </Paper>

      <Paper withBorder p="lg" radius="md">
        <Stack gap="lg">
          <Title order={4}>{t("kp.manage.booking_detail_completion")}</Title>
          <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="lg">
            <DetailField
              label={t("kp.manage.booking_details")}
              value={
                <Badge
                  color={booking.company_details_submitted ? "green" : "gray"}
                  variant="light"
                >
                  {booking.company_details_submitted
                    ? t("kp.manage.booking_details_submitted")
                    : t("kp.manage.booking_details_missing")}
                </Badge>
              }
            />
            <DetailField
              label={t("kp.manage.booking_status")}
              value={<KpBookingStatusBadge status={booking.status} />}
            />
          </SimpleGrid>
        </Stack>
      </Paper>

      <Paper withBorder p="lg" radius="md">
        <Stack gap="sm">
          <Title order={4}>{t("kp.manage.booking_services")}</Title>
          {booking.booked_services_count > 0 ? (
            <Text>{booking.booked_services_summary}</Text>
          ) : (
            <Text c="dimmed">{t("kp.manage.booking_services_empty")}</Text>
          )}
        </Stack>
      </Paper>
    </Stack>
  );
};

export default KpBookingDetails;
