import { Button, Group } from "@mantine/core";
import {
  IconArrowBackUp,
  IconCheck,
  IconTrash,
  IconX,
} from "@tabler/icons-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { StaffBookingResponse } from "../../orval/generated/fastAPI.schemas";
import {
  canAcceptBooking,
  canRejectBooking,
  canUndoAcceptBooking,
} from "../../utils/booking-status";
import BookingActionModals, {
  type BookingActionKind,
} from "./BookingActionModals";

const BookingActionBar = ({
  booking,
  eventId,
  onDeleted,
}: {
  booking: StaffBookingResponse;
  eventId: string;
  onDeleted: () => void;
}) => {
  const { t } = useTranslation();
  const [activeAction, setActiveAction] = useState<BookingActionKind | null>(
    null,
  );

  return (
    <>
      <Group gap="sm">
        <Button
          color="green"
          disabled={!canAcceptBooking(booking.status)}
          leftSection={<IconCheck size={16} />}
          onClick={() => setActiveAction("accept")}
        >
          {t("kp.manage.booking_action_accept")}
        </Button>
        <Button
          disabled={!canUndoAcceptBooking(booking.status)}
          leftSection={<IconArrowBackUp size={16} />}
          onClick={() => setActiveAction("undo_accept")}
          variant="default"
        >
          {t("kp.manage.booking_action_undo_accept")}
        </Button>
        <Button
          color="red"
          disabled={!canRejectBooking(booking.status)}
          leftSection={<IconX size={16} />}
          onClick={() => setActiveAction("reject")}
          variant="light"
        >
          {t("kp.manage.booking_action_reject")}
        </Button>
        <Button
          color="red"
          leftSection={<IconTrash size={16} />}
          onClick={() => setActiveAction("delete")}
          variant="outline"
        >
          {t("kp.manage.booking_action_delete")}
        </Button>
      </Group>

      <BookingActionModals
        booking={booking}
        eventId={eventId}
        kind={activeAction}
        onClose={() => setActiveAction(null)}
        onDeleted={onDeleted}
      />
    </>
  );
};

export default BookingActionBar;
