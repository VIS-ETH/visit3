import { Button, Group } from "@mantine/core";
import { IconArrowBackUp, IconCheck, IconEye } from "@tabler/icons-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { NavLink } from "react-router";
import type { StaffBookingResponse } from "../../orval/generated/fastAPI.schemas";
import {
  canAcceptBooking,
  canUndoAcceptBooking,
  hasNewAdditions,
} from "../../utils/booking-status";
import { KpBookingStatusBadge } from "../KpBookingStatusBadge";
import BookingActionModals, {
  type BookingActionKind,
} from "../staff-bookings/BookingActionModals";
import BookingNewAdditionsBadge from "../staff-bookings/BookingNewAdditionsBadge";

const CompanyBookingActions = ({
  booking,
  eventId,
}: {
  booking: StaffBookingResponse;
  eventId: string;
}) => {
  const { t } = useTranslation();
  const [activeAction, setActiveAction] = useState<BookingActionKind | null>(
    null,
  );

  return (
    <Group gap="xs" wrap="nowrap">
      <KpBookingStatusBadge status={booking.status} />
      {hasNewAdditions(booking) ? <BookingNewAdditionsBadge /> : null}
      {canAcceptBooking(booking.status) ? (
        <Button
          color="green"
          leftSection={<IconCheck size={14} />}
          onClick={() => setActiveAction("accept")}
          size="xs"
          variant="light"
        >
          {t("kp.manage.booking_action_accept")}
        </Button>
      ) : null}
      {canUndoAcceptBooking(booking.status) ? (
        <Button
          leftSection={<IconArrowBackUp size={14} />}
          onClick={() => setActiveAction("undo_accept")}
          size="xs"
          variant="default"
        >
          {t("kp.manage.booking_action_undo_accept")}
        </Button>
      ) : null}
      <Button
        component={NavLink}
        leftSection={<IconEye size={14} />}
        size="xs"
        to={`/kp/${eventId}/bookings/${booking.id}`}
        variant="subtle"
      >
        {t("company_management.view_booking")}
      </Button>
      <BookingActionModals
        booking={booking}
        eventId={eventId}
        kind={activeAction}
        onClose={() => setActiveAction(null)}
      />
    </Group>
  );
};

export default CompanyBookingActions;
