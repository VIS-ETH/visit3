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
import { NavLink, useLocation } from "react-router";
import {
  KpBookingStatus,
  type BookingResponse,
} from "../orval/generated/fastAPI.schemas";
import {
  getGetMyBookingQueryKey,
  useUpdateMyBookingStatus,
} from "../orval/generated/kp/kp";
import { profileFieldId } from "./company/company-profile-fields";
import { formatKpDisplayDate, isDeadlinePassed } from "../utils/kp-utils";
import { isInactiveBooking } from "../utils/my-booking";
import {
  bookingRequirementElementId,
  COMPANY_PROFILE_PATH,
} from "../utils/navigation";

const REQUIREMENT_ITEM_PREFIX = "requirement:";
const COMPANY_PROFILE_ITEM = "company_profile";
const COMPANY_DESCRIPTION_ITEM = "company_description";
const BILLING_ADDRESS_ITEM = "billing_address";
const GENERAL_EMAIL_ITEM = "general_email";
const PROFILE_FIELD_BY_ITEM: Record<string, string> = {
  [COMPANY_PROFILE_ITEM]: "description",
  [COMPANY_DESCRIPTION_ITEM]: "description",
  [BILLING_ADDRESS_ITEM]: "billing_company_name",
  [GENERAL_EMAIL_ITEM]: "general_email",
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

  return null;
};

export const KpBookingCompletion = ({
  booking,
  changeDeadline,
}: {
  booking: BookingResponse;
  changeDeadline: string;
}) => {
  const { t } = useTranslation();
  const { pathname } = useLocation();
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
    if (item === GENERAL_EMAIL_ITEM) {
      return t("kp.booking.missing_item_general_email");
    }
    return t("kp.booking.missing_item_unknown");
  };

  const missingItemHref = (item: string) => {
    if (item.startsWith(REQUIREMENT_ITEM_PREFIX)) {
      const requirementId = item.slice(REQUIREMENT_ITEM_PREFIX.length);
      return `/kp/${booking.event_id}/booking/${booking.id}/manage/services#${bookingRequirementElementId(requirementId)}`;
    }
    const profileField = PROFILE_FIELD_BY_ITEM[item];
    if (!profileField) return null;
    return `${COMPANY_PROFILE_PATH}?next=${encodeURIComponent(pathname)}#${profileFieldId(profileField)}`;
  };

  const missingItemsList = (items: string[]) => (
    <List size="sm" withPadding>
      {items.map((item) => {
        const href = missingItemHref(item);
        return (
          <List.Item key={item}>
            {href ? (
              <Anchor component={NavLink} to={href}>
                {missingItemLabel(item)}
              </Anchor>
            ) : (
              missingItemLabel(item)
            )}
          </List.Item>
        );
      })}
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
            <Text size="sm" fw={500}>
              {isDeadlinePassed(changeDeadline)
                ? t("error.kp_finalization_deadline_passed")
                : t("kp.booking.completeness_deadline", {
                    date: formatKpDisplayDate(changeDeadline),
                  })}
            </Text>
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
