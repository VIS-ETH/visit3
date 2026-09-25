import { Button, Group } from "@mantine/core";
import { IconArrowBackUp, IconCheck } from "@tabler/icons-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { StaffBookingResponse } from "../../orval/generated/fastAPI.schemas";
import {
  canAcceptBooking,
  canUndoAcceptBooking,
} from "../../utils/booking-status";
import { KpBookingStatusBadge } from "../KpBookingStatusBadge";
import BookingConfirmModal from "../bookings/BookingConfirmModal";
import { useBookingActions } from "../bookings/useBookingActions";

type CompanyBookingAction = "accept" | "undo_accept";

const CompanyBookingActions = ({
  booking,
  eventId,
}: {
  booking: StaffBookingResponse;
  eventId: string;
}) => {
  const { t } = useTranslation();
  const actions = useBookingActions(eventId);
  const [activeAction, setActiveAction] = useState<CompanyBookingAction | null>(
    null,
  );

  const runAction = async (run: () => Promise<void>) => {
    try {
      await run();
    } catch {
      return;
    }
    setActiveAction(null);
  };

  return (
    <Group gap="xs" wrap="nowrap">
      <KpBookingStatusBadge status={booking.status} />
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
      <BookingConfirmModal
        body={t("kp.manage.booking_accept_body")}
        color="green"
        isPending={actions.isAccepting}
        onClose={() => setActiveAction(null)}
        onConfirm={() => {
          void runAction(() => actions.acceptBooking(booking.id));
        }}
        opened={activeAction === "accept"}
        submitLabel={t("kp.manage.booking_accept_submit")}
        title={t("kp.manage.booking_accept_title")}
      />
      <BookingConfirmModal
        body={t("kp.manage.booking_undo_accept_body")}
        isPending={actions.isUndoingAccept}
        onClose={() => setActiveAction(null)}
        onConfirm={() => {
          void runAction(() => actions.undoAcceptBooking(booking.id));
        }}
        opened={activeAction === "undo_accept"}
        submitLabel={t("kp.manage.booking_undo_accept_submit")}
        title={t("kp.manage.booking_undo_accept_title")}
      />
    </Group>
  );
};

export default CompanyBookingActions;
