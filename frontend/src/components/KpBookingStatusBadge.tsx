import { Badge, type BadgeProps } from "@mantine/core";
import type { KpBookingStatus } from "../orval/generated/fastAPI.schemas";
import { BOOKING_STATUS_COLORS } from "../utils/kp-utils";

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
  return (
    <Badge
      color={BOOKING_STATUS_COLORS[status] ?? "gray"}
      variant={variant}
      size={size}
      {...props}
    >
      {status}
    </Badge>
  );
};
export default KpBookingStatusBadge;
