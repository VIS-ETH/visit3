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
import { IconAlertCircle, IconCheck } from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { NavLink } from "react-router";
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
const COMPANY_DESCRIPTION_ITEM = "company_description";
const BILLING_ADDRESS_ITEM = "billing_address";
const PROFILE_ITEMS = [
  COMPANY_PROFILE_ITEM,
  COMPANY_DESCRIPTION_ITEM,
  BILLING_ADDRESS_ITEM,
];

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

  return null;
};

export const KpBookingCompletion = ({
  booking,
}: {
  booking: BookingResponse;
}) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [isCancelOpen, setIsCancelOpen] = useState(false);
  const { mutateAsync: cancelStatus, isPending: isCancelling } =
    useUpdateMyBookingStatus();
  const missingItems = booking.missing_items ?? [];
  const requirementNames = requirementNamesById(booking);
  const isInactive = isInactiveBooking(booking);
  const canCancel = booking.status === KpBookingStatus.REGISTERED;

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
    if (item === COMPANY_DESCRIPTION_ITEM) {
      return t("kp.booking.missing_item_company_description");
    }
    if (item === BILLING_ADDRESS_ITEM) {
      return t("kp.booking.missing_item_billing_address");
    }
    return t("kp.booking.missing_item_unknown");
  };

  const isProfileItem = (item: string) => PROFILE_ITEMS.includes(item);

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
      {canCancel ? (
        <Group justify="flex-end">
          <Button
            color="red"
            loading={isCancelling}
            variant="light"
            onClick={() => setIsCancelOpen(true)}
          >
            {t("kp.booking.cancel_action")}
          </Button>
        </Group>
      ) : null}
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
