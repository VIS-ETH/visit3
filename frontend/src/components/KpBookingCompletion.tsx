import {
  Alert,
  Anchor,
  Badge,
  Button,
  Group,
  List,
  Modal,
  Stack,
  Text,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  IconAlertCircle,
  IconCheck,
  IconProgressCheck,
} from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { NavLink } from "react-router";
import { getApiErrorCode, getApiErrorDetails } from "../api/errors";
import {
  KpBookingStatus,
  type BookingResponse,
} from "../orval/generated/fastAPI.schemas";
import {
  getGetMyBookingQueryKey,
  useUpdateMyBookingStatus,
} from "../orval/generated/kp/kp";
import { isInactiveBooking } from "../utils/my-booking";
import { COMPANY_PROFILE_PATH } from "../utils/navigation";

const REQUIREMENT_ITEM_PREFIX = "requirement:";
const COMPANY_PROFILE_ITEM = "company_profile";
const BILLING_ADDRESS_ITEM = "billing_address";
const BOOKING_INCOMPLETE_CODE = "error.kp_booking_incomplete";

const blockingItemsFromError = (error: unknown): string[] => {
  if (getApiErrorCode(error) !== BOOKING_INCOMPLETE_CODE) return [];
  const missingItems = getApiErrorDetails(error)?.missingItems;
  if (!Array.isArray(missingItems)) return [];
  return missingItems.filter(
    (item): item is string => typeof item === "string",
  );
};

const requirementNamesById = (booking: BookingResponse) =>
  new Map(
    (booking.services ?? []).flatMap((bookingService) =>
      bookingService.service.requirements.map(
        (requirement) =>
          [
            requirement.id,
            `${bookingService.service.name} · ${requirement.name}`,
          ] as const,
      ),
    ),
  );

const BookingStatusNotice = ({ booking }: { booking: BookingResponse }) => {
  const { t } = useTranslation();

  if (booking.status === KpBookingStatus.REJECTED) {
    return (
      <Alert
        color="red"
        icon={<IconAlertCircle />}
        title={t("kp.booking.rejected_title")}
      >
        <Stack gap="xs">
          <Text size="sm">{t("kp.booking.rejected_body")}</Text>
          {booking.rejection_reason ? (
            <Text size="sm" fw={600}>
              {booking.rejection_reason}
            </Text>
          ) : null}
        </Stack>
      </Alert>
    );
  }

  if (booking.status === KpBookingStatus.CANCELLED) {
    return (
      <Alert
        color="gray"
        icon={<IconAlertCircle />}
        title={t("kp.booking.cancelled_title")}
      >
        {t("kp.booking.cancelled_body")}
      </Alert>
    );
  }

  if (booking.status === KpBookingStatus.CONFIRMED) {
    return (
      <Alert
        color="green"
        icon={<IconCheck />}
        title={t("kp.booking.confirmed_title")}
      >
        {t("kp.booking.confirmed_body")}
      </Alert>
    );
  }

  if (booking.status === KpBookingStatus.FINALIZED) {
    return (
      <Alert
        color="blue"
        icon={<IconProgressCheck />}
        title={t("kp.booking.finalized_title")}
      >
        {t("kp.booking.finalized_body")}
      </Alert>
    );
  }

  return null;
};

export const KpBookingCompletion = ({
  booking,
}: {
  booking: BookingResponse;
}) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [isConfirmOpen, setIsConfirmOpen] = useState(false);
  const [isCancelOpen, setIsCancelOpen] = useState(false);
  const [blockingItems, setBlockingItems] = useState<string[]>([]);
  const { mutateAsync: finalizeStatus, isPending: isFinalizing } =
    useUpdateMyBookingStatus();
  const { mutateAsync: cancelStatus, isPending: isCancelling } =
    useUpdateMyBookingStatus();
  const missingItems = booking.missing_items ?? [];
  const requirementNames = requirementNamesById(booking);
  const isInactive = isInactiveBooking(booking);
  const canFinalize = booking.status === KpBookingStatus.REGISTERED;
  const canCancel =
    booking.status === KpBookingStatus.REGISTERED ||
    booking.status === KpBookingStatus.FINALIZED;

  const missingItemLabel = (item: string) => {
    if (item.startsWith(REQUIREMENT_ITEM_PREFIX)) {
      const requirementId = item.slice(REQUIREMENT_ITEM_PREFIX.length);
      return (
        requirementNames.get(requirementId) ??
        t("kp.booking.missing_item_requirement")
      );
    }
    if (item === COMPANY_PROFILE_ITEM) {
      return t("kp.booking.missing_item_company_profile");
    }
    if (item === BILLING_ADDRESS_ITEM) {
      return t("kp.booking.missing_item_billing_address");
    }
    return t("kp.booking.missing_item_unknown");
  };

  const isProfileItem = (item: string) =>
    item === COMPANY_PROFILE_ITEM || item === BILLING_ADDRESS_ITEM;

  const missingItemsList = (items: string[]) => (
    <List size="sm" withPadding>
      {items.map((item) => (
        <List.Item key={item}>
          {isProfileItem(item) ? (
            <Anchor component={NavLink} to={COMPANY_PROFILE_PATH}>
              {missingItemLabel(item)}
            </Anchor>
          ) : (
            missingItemLabel(item)
          )}
        </List.Item>
      ))}
    </List>
  );

  const refreshBooking = () =>
    queryClient.invalidateQueries({
      queryKey: getGetMyBookingQueryKey(booking.event_id),
    });

  const finalizeBooking = async () => {
    try {
      await finalizeStatus({
        bookingId: booking.id,
        data: { status: KpBookingStatus.FINALIZED },
      });
    } catch (error) {
      setBlockingItems(blockingItemsFromError(error));
      return;
    }
    setBlockingItems([]);
    setIsConfirmOpen(false);
    notifications.show({
      color: "green",
      message: t("kp.booking.finalize_success"),
    });
    void refreshBooking();
  };

  const cancelBooking = async () => {
    try {
      await cancelStatus({
        bookingId: booking.id,
        data: { status: KpBookingStatus.CANCELLED },
      });
    } catch {
      return;
    }
    setIsCancelOpen(false);
    notifications.show({
      color: "green",
      message: t("kp.booking.cancel_success"),
    });
    void refreshBooking();
  };

  if (isInactive) {
    return <BookingStatusNotice booking={booking} />;
  }

  return (
    <Stack gap="md">
      <BookingStatusNotice booking={booking} />
      {booking.is_complete ? (
        <Badge
          color="green"
          leftSection={<IconCheck size={12} />}
          variant="light"
          w="fit-content"
        >
          {t("kp.booking.completeness_complete")}
        </Badge>
      ) : (
        <Alert
          color="yellow"
          icon={<IconAlertCircle />}
          title={t("kp.booking.completeness_incomplete")}
        >
          <Stack gap="xs">
            <Text size="sm">
              {t("kp.booking.completeness_incomplete_body")}
            </Text>
            {missingItemsList(missingItems)}
          </Stack>
        </Alert>
      )}
      {canFinalize || canCancel ? (
        <Group justify="flex-end">
          {canCancel ? (
            <Button
              color="red"
              loading={isCancelling}
              variant="light"
              onClick={() => setIsCancelOpen(true)}
            >
              {t("kp.booking.cancel_action")}
            </Button>
          ) : null}
          {canFinalize ? (
            <Button
              disabled={!booking.is_complete}
              loading={isFinalizing}
              onClick={() => setIsConfirmOpen(true)}
            >
              {t("kp.booking.finalize_action")}
            </Button>
          ) : null}
        </Group>
      ) : null}
      <Modal
        centered
        opened={isConfirmOpen}
        onClose={() => setIsConfirmOpen(false)}
        title={t("kp.booking.finalize_confirm_title")}
      >
        <Stack gap="md">
          <Text size="sm">{t("kp.booking.finalize_confirm_body")}</Text>
          {blockingItems.length > 0 ? (
            <Alert
              color="red"
              icon={<IconAlertCircle />}
              title={t("error.kp_booking_incomplete")}
            >
              {missingItemsList(blockingItems)}
            </Alert>
          ) : null}
          <Group justify="flex-end">
            <Button variant="subtle" onClick={() => setIsConfirmOpen(false)}>
              {t("common.cancel")}
            </Button>
            <Button
              loading={isFinalizing}
              onClick={() => {
                void finalizeBooking();
              }}
            >
              {t("kp.booking.finalize_confirm_submit")}
            </Button>
          </Group>
        </Stack>
      </Modal>
      <Modal
        centered
        opened={isCancelOpen}
        onClose={() => setIsCancelOpen(false)}
        title={t("kp.booking.cancel_confirm_title")}
      >
        <Stack gap="md">
          <Text size="sm">{t("kp.booking.cancel_confirm_body")}</Text>
          <Group justify="flex-end">
            <Button variant="subtle" onClick={() => setIsCancelOpen(false)}>
              {t("kp.booking.cancel_confirm_keep")}
            </Button>
            <Button
              color="red"
              loading={isCancelling}
              onClick={() => {
                void cancelBooking();
              }}
            >
              {t("kp.booking.cancel_confirm_submit")}
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
};
