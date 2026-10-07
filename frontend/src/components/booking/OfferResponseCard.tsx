import {
  Alert,
  Button,
  Card,
  Group,
  Modal,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconClockHour4, IconTicket } from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  KpBookingStatus,
  type BookingResponse,
  type KpResponse,
} from "../../orval/generated/fastAPI.schemas";
import { useGetMyCompany } from "../../orval/generated/company/company";
import {
  getGetMyBookingQueryKey,
  useAcceptBookingOffer,
  useUpdateMyBookingStatus,
} from "../../orval/generated/kp/kp";
import { formatKpDisplayDate } from "../../utils/kp-utils";
import { isOfferOpen } from "../../utils/my-booking";
import { formatPrice } from "../../utils/price-utils";
import { KpBookingRecap } from "../KpBookingRecap";
import { KpBoothZoneColorSwatch } from "../KpBoothZoneColorSwatch";
import BookingConsentChecks from "./BookingConsentChecks";
import BookingProfileConfirmation from "./BookingProfileConfirmation";

const OfferResponseCard = ({
  event,
  booking,
}: {
  event: KpResponse;
  booking: BookingResponse;
}) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data: company } = useGetMyCompany();
  const [isConfirmOpen, setIsConfirmOpen] = useState(false);
  const [isDeclineOpen, setIsDeclineOpen] = useState(false);
  const [isProfileConfirmed, setIsProfileConfirmed] = useState(false);
  const [agbAccepted, setAgbAccepted] = useState(false);
  const [bindingAccepted, setBindingAccepted] = useState(false);
  const { mutateAsync: accept, isPending: isAccepting } =
    useAcceptBookingOffer();
  const { mutateAsync: updateStatus, isPending: isDeclining } =
    useUpdateMyBookingStatus();
  const isOpen = isOfferOpen(booking);
  const deadline = formatKpDisplayDate(booking.offer_deadline ?? "");
  const canConfirm =
    Boolean(company?.profile_bookable) &&
    isProfileConfirmed &&
    agbAccepted &&
    bindingAccepted;

  const refreshBooking = () =>
    queryClient.invalidateQueries({
      queryKey: getGetMyBookingQueryKey(booking.event_id),
    });

  const confirmBooking = async () => {
    try {
      await accept({
        bookingId: booking.id,
        data: { confirm_profile: true, accept_terms: true },
      });
    } catch {
      return;
    }
    setIsConfirmOpen(false);
    notifications.show({ color: "green", message: t("kp.offer.confirmed") });
    void refreshBooking();
  };

  const declineOffer = async () => {
    try {
      await updateStatus({
        bookingId: booking.id,
        data: { status: KpBookingStatus.CANCELLED },
      });
    } catch {
      return;
    }
    setIsDeclineOpen(false);
    notifications.show({ color: "green", message: t("kp.offer.declined") });
    void refreshBooking();
  };

  return (
    <Card withBorder radius="md" p="lg">
      <Stack gap="md">
        <Group gap="sm">
          <IconTicket size={20} />
          <Title order={4}>{t("kp.offer.title")}</Title>
        </Group>
        <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="sm">
          <div>
            <Text size="sm" c="dimmed">
              {t("kp.company_view.booking_zone")}
            </Text>
            <Group gap="xs" align="center">
              {booking.booth_zone ? (
                <KpBoothZoneColorSwatch color={booking.booth_zone.color} />
              ) : null}
              <Text fw={500}>
                {booking.booth_zone?.name ?? booking.booth_zone_id}
              </Text>
            </Group>
          </div>
          <div>
            <Text size="sm" c="dimmed">
              {t("kp.company_view.booking_total_gross")}
            </Text>
            <Text fw={500}>
              {t("common.currency")} {formatPrice(booking.price.gross)}
            </Text>
          </div>
        </SimpleGrid>
        {isOpen ? (
          <>
            <Alert color="grape" icon={<IconClockHour4 />}>
              {t("kp.offer.deadline_notice", { date: deadline })}
            </Alert>
            <Group justify="flex-end" gap="sm">
              <Button
                color="red"
                variant="light"
                onClick={() => setIsDeclineOpen(true)}
              >
                {t("kp.offer.decline")}
              </Button>
              <Button onClick={() => setIsConfirmOpen(true)}>
                {t("kp.offer.confirm")}
              </Button>
            </Group>
          </>
        ) : (
          <Alert color="gray" icon={<IconClockHour4 />}>
            {t("kp.offer.expired")}
          </Alert>
        )}
      </Stack>
      <Modal
        centered
        size="lg"
        opened={isConfirmOpen}
        onClose={() => setIsConfirmOpen(false)}
        title={t("kp.offer.confirm_title")}
      >
        <Stack gap="md">
          <KpBookingRecap
            booking={booking}
            vatRatePercent={event.vat_rate_percent}
          />
          <BookingProfileConfirmation
            returnPath={`/kp/${event.id}`}
            company={company}
            isConfirmed={isProfileConfirmed}
            onConfirmedChange={setIsProfileConfirmed}
          />
          <Stack gap="sm">
            <BookingConsentChecks
              termsUrl={event.terms_url}
              agbAccepted={agbAccepted}
              bindingAccepted={bindingAccepted}
              onAgbChange={setAgbAccepted}
              onBindingChange={setBindingAccepted}
              highlight={false}
            />
          </Stack>
          <Group justify="flex-end">
            <Button variant="subtle" onClick={() => setIsConfirmOpen(false)}>
              {t("common.cancel")}
            </Button>
            <Button
              disabled={!canConfirm}
              loading={isAccepting}
              onClick={() => {
                void confirmBooking();
              }}
            >
              {t("kp.offer.confirm_submit")}
            </Button>
          </Group>
        </Stack>
      </Modal>
      <Modal
        centered
        opened={isDeclineOpen}
        onClose={() => setIsDeclineOpen(false)}
        title={t("kp.offer.decline_title")}
      >
        <Stack gap="md">
          <Text size="sm">{t("kp.offer.decline_body")}</Text>
          <Group justify="flex-end">
            <Button variant="subtle" onClick={() => setIsDeclineOpen(false)}>
              {t("kp.offer.decline_keep")}
            </Button>
            <Button
              color="red"
              loading={isDeclining}
              onClick={() => {
                void declineOffer();
              }}
            >
              {t("kp.offer.decline_submit")}
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Card>
  );
};

export default OfferResponseCard;
