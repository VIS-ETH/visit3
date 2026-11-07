import { ActionIcon, Menu } from "@mantine/core";
import {
  IconArrowBackUp,
  IconBuilding,
  IconCheck,
  IconDotsVertical,
  IconExternalLink,
  IconTrash,
  IconUsers,
  IconX,
} from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import type { KpBookingStatus } from "../../orval/generated/fastAPI.schemas";
import {
  canAcceptBooking,
  canRejectBooking,
  canUndoAcceptBooking,
} from "../../utils/booking-status";

export type BookingRowActionKind =
  "open" | "accept" | "undo_accept" | "reject" | "delete";

const BookingRowActions = ({
  companyId,
  onAction,
  status,
}: {
  companyId: string;
  onAction: (action: BookingRowActionKind) => void;
  status: KpBookingStatus;
}) => {
  const { t } = useTranslation();

  return (
    <Menu position="bottom-end" shadow="md" withinPortal>
      <Menu.Target>
        <ActionIcon
          aria-label={t("kp.manage.booking_actions")}
          color="gray"
          variant="subtle"
        >
          <IconDotsVertical size={16} />
        </ActionIcon>
      </Menu.Target>
      <Menu.Dropdown>
        <Menu.Item
          leftSection={<IconExternalLink size={16} />}
          onClick={() => onAction("open")}
        >
          {t("kp.manage.booking_action_open")}
        </Menu.Item>
        <Menu.Item
          component={Link}
          leftSection={<IconBuilding size={16} />}
          to={`/company-management?company=${companyId}`}
        >
          {t("kp.manage.booking_action_view_company")}
        </Menu.Item>
        <Menu.Item
          component={Link}
          leftSection={<IconUsers size={16} />}
          to={`/user-management?company=${companyId}`}
        >
          {t("kp.manage.booking_action_view_users")}
        </Menu.Item>
        <Menu.Item
          disabled={!canAcceptBooking(status)}
          leftSection={<IconCheck size={16} />}
          onClick={() => onAction("accept")}
        >
          {t("kp.manage.booking_action_accept")}
        </Menu.Item>
        <Menu.Item
          disabled={!canUndoAcceptBooking(status)}
          leftSection={<IconArrowBackUp size={16} />}
          onClick={() => onAction("undo_accept")}
        >
          {t("kp.manage.booking_action_undo_accept")}
        </Menu.Item>
        <Menu.Item
          color="red"
          disabled={!canRejectBooking(status)}
          leftSection={<IconX size={16} />}
          onClick={() => onAction("reject")}
        >
          {t("kp.manage.booking_action_reject")}
        </Menu.Item>
        <Menu.Item
          color="red"
          leftSection={<IconTrash size={16} />}
          onClick={() => onAction("delete")}
        >
          {t("kp.manage.booking_action_delete")}
        </Menu.Item>
      </Menu.Dropdown>
    </Menu>
  );
};

export default BookingRowActions;
