import {
  Button,
  Group,
  Pagination,
  Paper,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { IconDownload, IconGift } from "@tabler/icons-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";
import type { StaffBookingResponse } from "../../orval/generated/fastAPI.schemas";
import {
  downloadEventBookingsCsv,
  useListEventBookings,
} from "../../orval/generated/kp/kp";
import { useAsyncAction } from "../../hooks/use-async-action";
import { canAcceptBooking } from "../../utils/booking-status";
import { downloadBlob } from "../../utils/download";
import ErrorAlert from "../ErrorAlert";
import PageLoader from "../PageLoader";
import BookingActionModals, {
  type BookingActionKind,
} from "../staff-bookings/BookingActionModals";
import type { BookingRowActionKind } from "../staff-bookings/BookingRowActions";
import OfferBookingModal from "../staff-bookings/OfferBookingModal";
import { useBookingActions } from "../staff-bookings/useBookingActions";
import BookingsFilters from "./bookings/BookingsFilters";
import BookingsTable from "./bookings/BookingsTable";
import { useBookingFilters } from "./bookings/use-booking-filters";

const BookingsTab = ({
  eventId,
  canOffer = false,
}: {
  eventId: string;
  canOffer?: boolean;
}) => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data: bookings, isLoading, isError } = useListEventBookings(eventId);
  const actions = useBookingActions(eventId);
  const filters = useBookingFilters(bookings);
  const [isOfferOpen, setIsOfferOpen] = useState(false);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [activeAction, setActiveAction] = useState<{
    booking: StaffBookingResponse;
    kind: BookingActionKind;
  } | null>(null);

  const acceptableSelectedIds = filters.visibleRows
    .filter(
      (booking) =>
        selectedIds.includes(booking.id) && canAcceptBooking(booking.status),
    )
    .map((booking) => booking.id);

  const { run: acceptSelected, isRunning: isAcceptingSelected } =
    useAsyncAction(async () => {
      await actions.acceptBookings(acceptableSelectedIds);
      setSelectedIds([]);
    });

  const { run: exportCsv, isRunning: isExporting } = useAsyncAction(
    async () => {
      const content = await downloadEventBookingsCsv(eventId, {
        responseType: "blob",
      });
      downloadBlob(content, "bookings.csv");
    },
  );

  const handleRowAction = (
    action: BookingRowActionKind,
    booking: StaffBookingResponse,
  ) => {
    if (action === "open") {
      void navigate(`/kp/${eventId}/bookings/${booking.id}`);
      return;
    }
    setActiveAction({ booking, kind: action });
  };

  return (
    <Paper withBorder p="lg" radius="md">
      <Stack gap="sm">
        <Group justify="space-between" align="flex-end">
          <Title order={4}>{t("kp.manage.bookings_title")}</Title>
          <Group gap="sm">
            {canOffer ? (
              <Button
                leftSection={<IconGift size={16} />}
                onClick={() => setIsOfferOpen(true)}
                variant="default"
              >
                {t("kp.manage.offer_button")}
              </Button>
            ) : null}
            <Button
              disabled={acceptableSelectedIds.length === 0}
              loading={isAcceptingSelected}
              onClick={() => {
                void acceptSelected();
              }}
            >
              {t("kp.manage.bookings_accept_selected", {
                amount: acceptableSelectedIds.length,
              })}
            </Button>
            <Button
              leftSection={<IconDownload size={16} />}
              loading={isExporting}
              onClick={() => {
                void exportCsv();
              }}
              variant="default"
            >
              {t("kp.manage.bookings_export_csv")}
            </Button>
          </Group>
        </Group>

        <BookingsFilters filters={filters} />

        {isLoading ? (
          <PageLoader />
        ) : isError ? (
          <ErrorAlert />
        ) : !filters.hasBookings ? (
          <Text c="dimmed">{t("kp.manage.bookings_empty")}</Text>
        ) : filters.visibleRows.length === 0 ? (
          <Text c="dimmed">{t("kp.manage.bookings_no_results")}</Text>
        ) : (
          <BookingsTable
            eventId={eventId}
            rows={filters.pageRows}
            sort={filters.sort}
            onSort={filters.toggleSort}
            selectedIds={selectedIds}
            onSelectionChange={setSelectedIds}
            onAction={handleRowAction}
            onSaveBoothNr={(bookingId, boothNr) =>
              actions.updateBooking(bookingId, { booth_nr: boothNr })
            }
          />
        )}

        {filters.pageCount > 1 ? (
          <Group justify="space-between">
            <Text c="dimmed" size="sm">
              {t("kp.manage.bookings_page_summary", {
                shown: filters.pageRows.length,
                total: filters.visibleRows.length,
              })}
            </Text>
            <Pagination
              onChange={filters.setPage}
              total={filters.pageCount}
              value={filters.currentPage}
            />
          </Group>
        ) : null}
      </Stack>

      <BookingActionModals
        booking={activeAction?.booking}
        eventId={eventId}
        kind={activeAction?.kind ?? null}
        onClose={() => setActiveAction(null)}
      />
      {canOffer ? (
        <OfferBookingModal
          eventId={eventId}
          opened={isOfferOpen}
          onClose={() => setIsOfferOpen(false)}
        />
      ) : null}
    </Paper>
  );
};

export default BookingsTab;
