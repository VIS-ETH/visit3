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
  deleteRequiresForce,
} from "../../utils/booking-status";
import BookingConfirmModal from "./BookingConfirmModal";
import BookingDeleteModal from "./BookingDeleteModal";
import BookingRejectModal from "./BookingRejectModal";
import { useBookingActions } from "./useBookingActions";

type BookingActionKind = "accept" | "undo_accept" | "reject" | "delete";

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
  const actions = useBookingActions(eventId);
  const [activeAction, setActiveAction] = useState<BookingActionKind | null>(
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
      <BookingRejectModal
        isPending={actions.isRejecting}
        onClose={() => setActiveAction(null)}
        onConfirm={(reason) => {
          void runAction(() => actions.rejectBooking(booking.id, reason));
        }}
        opened={activeAction === "reject"}
      />
      <BookingDeleteModal
        isPending={actions.isDeleting}
        onClose={() => setActiveAction(null)}
        onConfirm={(force) => {
          void runAction(async () => {
            await actions.deleteBooking(booking.id, force);
            onDeleted();
          });
        }}
        opened={activeAction === "delete"}
        requiresForce={deleteRequiresForce(booking.status)}
      />
    </>
  );
};

export default BookingActionBar;
