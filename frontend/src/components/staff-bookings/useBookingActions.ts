import { useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import type { StaffUpdateBookingRequest } from "../../orval/generated/fastAPI.schemas";
import {
  getGetEventBookingQueryKey,
  getListEventBookingsQueryKey,
  useAcceptBooking,
  useAcknowledgeBookingAdditions,
  useDeleteBooking,
  useRejectBooking,
  useUndoAcceptBooking,
  useUpdateBooking,
} from "../../orval/generated/kp/kp";
import { notifySuccess } from "../../utils/notify";

export const useBookingActions = (eventId: string) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const accept = useAcceptBooking();
  const acknowledge = useAcknowledgeBookingAdditions();
  const undoAccept = useUndoAcceptBooking();
  const reject = useRejectBooking();
  const update = useUpdateBooking();
  const remove = useDeleteBooking();

  const refreshList = () =>
    queryClient.invalidateQueries({
      queryKey: getListEventBookingsQueryKey(eventId),
    });

  const refreshBooking = async (bookingId: string) => {
    await Promise.all([
      refreshList(),
      queryClient.invalidateQueries({
        queryKey: getGetEventBookingQueryKey(eventId, bookingId),
      }),
    ]);
  };

  const acceptBooking = async (bookingId: string) => {
    await accept.mutateAsync({ bookingId });
    await refreshBooking(bookingId);
    notifySuccess(t("kp.manage.booking_accepted"));
  };

  const acceptBookings = async (bookingIds: string[]) => {
    try {
      for (const bookingId of bookingIds) {
        await accept.mutateAsync({ bookingId });
      }
    } finally {
      await refreshList();
    }
    notifySuccess(
      t("kp.manage.bookings_accepted", { amount: bookingIds.length }),
    );
  };

  const acknowledgeAdditions = async (bookingId: string) => {
    await acknowledge.mutateAsync({ bookingId });
    await refreshBooking(bookingId);
    notifySuccess(t("kp.manage.booking_additions_acknowledged"));
  };

  const undoAcceptBooking = async (bookingId: string) => {
    await undoAccept.mutateAsync({ bookingId });
    await refreshBooking(bookingId);
    notifySuccess(t("kp.manage.booking_undo_accepted"));
  };

  const rejectBooking = async (bookingId: string, reason: string) => {
    await reject.mutateAsync({ bookingId, data: { reason } });
    await refreshBooking(bookingId);
    notifySuccess(t("kp.manage.booking_rejected"));
  };

  const deleteBooking = async (bookingId: string, force: boolean) => {
    await remove.mutateAsync({ bookingId, params: { force } });
    await refreshList();
    notifySuccess(t("kp.manage.booking_deleted"));
  };

  const updateBooking = async (
    bookingId: string,
    data: StaffUpdateBookingRequest,
  ) => {
    const updated = await update.mutateAsync({ bookingId, data });
    await refreshBooking(bookingId);
    notifySuccess(t("kp.manage.booking_updated"));
    return updated;
  };

  return {
    acceptBooking,
    acceptBookings,
    acknowledgeAdditions,
    deleteBooking,
    rejectBooking,
    undoAcceptBooking,
    updateBooking,
  };
};
