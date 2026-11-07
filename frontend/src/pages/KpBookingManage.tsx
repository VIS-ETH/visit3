import {
  ActionIcon,
  Alert,
  Button,
  Group,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { IconAlertCircle, IconArrowBackUp } from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Navigate, useNavigate, useParams } from "react-router";
import BackButton from "../components/BackButton";
import ErrorAlert from "../components/ErrorAlert";
import PageLoader from "../components/PageLoader";
import { KpBookingCompletion } from "../components/exhibitor-booking/KpBookingCompletion";
import { isFinalizationDeadlinePassed } from "../components/exhibitor-booking/booking-zone-access";
import AddServicesForm from "../components/exhibitor-booking/manage/AddServicesForm";
import DiscardChangesModal from "../components/exhibitor-booking/manage/DiscardChangesModal";
import RequirementChangesConfirmModal from "../components/exhibitor-booking/manage/RequirementChangesConfirmModal";
import RequirementsPromptModal from "../components/exhibitor-booking/manage/RequirementsPromptModal";
import RequirementsSection from "../components/exhibitor-booking/manage/RequirementsSection";
import { useRequirementChanges } from "../components/exhibitor-booking/manage/use-requirement-changes";
import { useScrollToHash } from "../hooks/use-scroll-to-hash";
import { useWarnOnLeave } from "../hooks/use-warn-on-leave";
import type {
  BookingResponse,
  BookingServiceResponse,
} from "../orval/generated/fastAPI.schemas";
import {
  getGetMyBookingQueryKey,
  useGetKpById,
  useGetMyBooking,
} from "../orval/generated/kp/kp";
import { isManageableBooking } from "../utils/my-booking";

const KpBookingManage = () => {
  const { t } = useTranslation();
  useScrollToHash();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const changes = useRequirementChanges();
  const [confirmRequirementsOpen, setConfirmRequirementsOpen] = useState(false);
  const [pendingNavigationTo, setPendingNavigationTo] = useState<string | null>(
    null,
  );
  const [promptedServices, setPromptedServices] = useState<
    BookingServiceResponse[]
  >([]);
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
    isError: isBookingError,
  } = useGetMyBooking(eventId, {
    query: { enabled: Boolean(eventId) },
  });
  const hasPendingChanges = changes.changeList.length > 0;
  useWarnOnLeave(hasPendingChanges || changes.isSaving);

  if (isLoadingEvent || isLoadingBooking) return <PageLoader />;

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
        <ErrorAlert>{t("kp.booking.error")}</ErrorAlert>
      </Stack>
    );
  }

  if (!isManageableBooking(booking)) {
    return <Navigate to={`/kp/${eventId}`} replace />;
  }

  const bookingServices = booking.services ?? [];
  const isEditable = !isFinalizationDeadlinePassed(event);
  const isPrompted = (bookingServiceId: string) =>
    promptedServices.some((prompted) => prompted.id === bookingServiceId);
  const listedServices = bookingServices.filter(
    (bookingService) => !isPrompted(bookingService.id),
  );
  const promptedChanges = changes.changeList.filter((change) =>
    isPrompted(change.bookingServiceId),
  );

  const handleServicesAdded = async (
    updated: BookingResponse,
    serviceIds: string[],
  ) => {
    await queryClient.invalidateQueries({
      queryKey: getGetMyBookingQueryKey(eventId),
    });
    setPromptedServices(
      (updated.services ?? []).filter(
        (bookingService) =>
          serviceIds.includes(bookingService.service_id) &&
          bookingService.service.requirements.length > 0,
      ),
    );
  };

  const saveAllChanges = async () => {
    if (await changes.save(changes.changeList)) {
      setConfirmRequirementsOpen(false);
      setPromptedServices([]);
    }
  };

  const savePromptedChanges = async () => {
    if (await changes.save(promptedChanges)) setPromptedServices([]);
  };

  const navigateOrConfirmDiscard = (to: string) => {
    if (hasPendingChanges) {
      setPendingNavigationTo(to);
      return;
    }
    navigate(to);
  };

  return (
    <Stack gap="md">
      <DiscardChangesModal
        opened={pendingNavigationTo !== null}
        onStay={() => setPendingNavigationTo(null)}
        onDiscard={() => {
          const to = pendingNavigationTo;
          changes.discardAll();
          setPendingNavigationTo(null);
          if (to) navigate(to);
        }}
      />
      <RequirementChangesConfirmModal
        changes={changes.changeList}
        isSaving={changes.isSaving}
        opened={confirmRequirementsOpen}
        onClose={() => setConfirmRequirementsOpen(false)}
        onSubmit={() => {
          void saveAllChanges();
        }}
      />
      <RequirementsPromptModal
        bookingServices={promptedServices}
        changes={changes}
        editable={isEditable}
        onClose={() => setPromptedServices([])}
        onSave={() => {
          void savePromptedChanges();
        }}
        promptedChangeCount={promptedChanges.length}
      />
      <ActionIcon
        aria-label={t("kp.booking_manage.back_to_manage")}
        radius="md"
        size="input-md"
        variant="transparent"
        onClick={() =>
          navigateOrConfirmDiscard(
            `/kp/${eventId}/booking/${booking.id}/manage`,
          )
        }
      >
        <IconArrowBackUp />
      </ActionIcon>
      <Group justify="space-between" align="flex-start">
        <div>
          <Title order={2}>{t("kp.booking_manage.services_page_title")}</Title>
          <Text c="dimmed" size="sm">
            {t("kp.booking_manage.services_page_subtitle", {
              eventName: event.name,
              bookingNumber: booking.booking_number,
            })}
          </Text>
        </div>
        <Button
          variant="light"
          onClick={() =>
            navigateOrConfirmDiscard(`/kp/${eventId}/booking/${booking.id}`)
          }
        >
          {t("kp.booking_manage.view_summary")}
        </Button>
      </Group>

      {!isEditable ? (
        <Alert icon={<IconAlertCircle />} color="yellow">
          {t("kp.booking_manage.deadline_notice")}
        </Alert>
      ) : null}

      <KpBookingCompletion
        booking={booking}
        changeDeadline={event.finalization_deadline}
      />

      {hasPendingChanges ? (
        <Alert icon={<IconAlertCircle />} color="yellow">
          {t("kp.booking_manage.unsaved_changes_notice", {
            count: changes.changeList.length,
          })}
        </Alert>
      ) : null}

      <AddServicesForm
        bookingId={booking.id}
        bookingServices={bookingServices}
        editable={isEditable}
        eventId={eventId}
        onAdded={handleServicesAdded}
        vatRatePercent={event.vat_rate_percent}
      />

      <RequirementsSection
        bookingServices={bookingServices}
        changes={changes}
        editable={isEditable}
        listedServices={listedServices}
        onSave={() => setConfirmRequirementsOpen(true)}
      />
    </Stack>
  );
};

export default KpBookingManage;
