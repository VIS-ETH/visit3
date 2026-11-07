import { useTranslation } from "react-i18next";
import type { StaffBookingResponse } from "../../orval/generated/fastAPI.schemas";
import { deleteRequiresForce } from "../../utils/booking-status";
import BookingConfirmModal from "./BookingConfirmModal";
import BookingDeleteModal from "./BookingDeleteModal";
import BookingRejectModal from "./BookingRejectModal";
import { useBookingActions } from "./useBookingActions";

export type BookingActionKind = "accept" | "undo_accept" | "reject" | "delete";

const BookingActionModals = ({
  booking,
  kind,
  eventId,
  onClose,
  onDeleted,
}: {
  booking: StaffBookingResponse | undefined;
  kind: BookingActionKind | null;
  eventId: string;
  onClose: () => void;
  onDeleted?: () => void;
}) => {
  const { t } = useTranslation();
  const actions = useBookingActions(eventId);

  const runThenClose = async (
    action: (bookingId: string) => Promise<unknown>,
  ) => {
    if (!booking) return;
    await action(booking.id);
    onClose();
  };

  return (
    <>
      <BookingConfirmModal
        body={t("kp.manage.booking_accept_body")}
        color="green"
        onClose={onClose}
        onConfirm={() => runThenClose(actions.acceptBooking)}
        opened={kind === "accept"}
        submitLabel={t("kp.manage.booking_accept_submit")}
        title={t("kp.manage.booking_accept_title")}
      />
      <BookingConfirmModal
        body={t("kp.manage.booking_undo_accept_body")}
        onClose={onClose}
        onConfirm={() => runThenClose(actions.undoAcceptBooking)}
        opened={kind === "undo_accept"}
        submitLabel={t("kp.manage.booking_undo_accept_submit")}
        title={t("kp.manage.booking_undo_accept_title")}
      />
      <BookingRejectModal
        onClose={onClose}
        onConfirm={(reason) =>
          runThenClose((bookingId) => actions.rejectBooking(bookingId, reason))
        }
        opened={kind === "reject"}
      />
      <BookingDeleteModal
        onClose={onClose}
        onConfirm={async (force) => {
          await runThenClose((bookingId) =>
            actions.deleteBooking(bookingId, force),
          );
          onDeleted?.();
        }}
        opened={kind === "delete"}
        requiresForce={booking ? deleteRequiresForce(booking.status) : false}
      />
    </>
  );
};

export default BookingActionModals;
