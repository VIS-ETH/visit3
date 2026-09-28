import { Text, Timeline } from "@mantine/core";
import {
  IconCheck,
  IconClock,
  IconX,
} from "@tabler/icons-react";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import {
  KpBookingStatus,
  type StaffBookingResponse,
} from "../../orval/generated/fastAPI.schemas";
import { formatBookingTimestamp } from "./booking-format";

type TimelineStep = {
  bullet: ReactNode;
  isDone: boolean;
  key: string;
  timestamp?: string | null;
  title: string;
};

const BookingStatusTimeline = ({
  booking,
}: {
  booking: StaffBookingResponse;
}) => {
  const { t } = useTranslation();
  const isRejected = booking.status === KpBookingStatus.REJECTED;

  const steps: TimelineStep[] = [
    {
      bullet: <IconClock size={12} />,
      isDone: true,
      key: "registered",
      timestamp:
        booking.status === KpBookingStatus.REGISTERED
          ? booking.status_changed_at
          : undefined,
      title: t("kp.manage.booking_timeline_registered"),
    },
    isRejected
      ? {
          bullet: <IconX size={12} />,
          isDone: true,
          key: "rejected",
          timestamp: booking.status_changed_at,
          title: t("kp.manage.booking_timeline_rejected"),
        }
      : {
          bullet: <IconCheck size={12} />,
          isDone: Boolean(booking.confirmed_at),
          key: "confirmed",
          timestamp: booking.confirmed_at,
          title: t("kp.manage.booking_timeline_confirmed"),
        },
  ];

  const doneCount = steps.filter((step) => step.isDone).length;

  return (
    <Timeline
      active={doneCount - 1}
      bulletSize={22}
      color={isRejected ? "red" : "blue"}
      lineWidth={2}
    >
      {steps.map((step) => {
        const timestamp = formatBookingTimestamp(step.timestamp);
        return (
          <Timeline.Item bullet={step.bullet} key={step.key} title={step.title}>
            {timestamp ? (
              <Text c="dimmed" size="xs">
                {timestamp}
              </Text>
            ) : step.isDone ? null : (
              <Text c="dimmed" size="xs">
                {t("kp.manage.booking_timeline_pending")}
              </Text>
            )}
          </Timeline.Item>
        );
      })}
    </Timeline>
  );
};

export default BookingStatusTimeline;
