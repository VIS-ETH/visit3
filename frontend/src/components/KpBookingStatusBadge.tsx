import { Badge, type BadgeProps } from "@mantine/core";
import { useTranslation } from "react-i18next";
import type { KpBookingStatus } from "../orval/generated/fastAPI.schemas";
import {
  BOOKING_STATUS_COLORS,
  BOOKING_STATUS_LABEL_KEYS,
} from "../utils/kp-utils";

export type KpBookingStatusBadgeProps = Omit<
  BadgeProps,
  "color" | "children"
> & {
  status: KpBookingStatus;
};

export const KpBookingStatusBadge = ({
  status,
  variant = "light",
  size = "sm",
  ...props
}: KpBookingStatusBadgeProps) => {
  const { t } = useTranslation();

  return (
    <Badge
      color={BOOKING_STATUS_COLORS[status]}
      variant={variant}
      size={size}
      {...props}
    >
      {t(BOOKING_STATUS_LABEL_KEYS[status])}
    </Badge>
  );
};
export default KpBookingStatusBadge;
