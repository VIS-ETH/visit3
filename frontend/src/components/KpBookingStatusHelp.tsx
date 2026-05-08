import {
  Modal,
  Stack,
  Text,
  Tooltip,
  UnstyledButton,
  VisuallyHidden,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { useTranslation } from "react-i18next";
import type { KpBookingStatus } from "../orval/generated/fastAPI.schemas";
import { KpBookingStatusBadge } from "./KpBookingStatusBadge";

const BOOKING_STATUSES: KpBookingStatus[] = [
  // "DRAFT", not used at the moment
  "REGISTERED",
  "FINALIZED",
  "CONFIRMED",
  "CANCELLED",
];

export const KpBookingStatusHelp = () => {
  const { t } = useTranslation();
  const [opened, { open, close }] = useDisclosure(false);

  return (
    <>
      <Tooltip label={t("kp.booking.status_help_open_label")}>
        <UnstyledButton
          type="button"
          onClick={open}
          aria-label={t("kp.booking.status_help_open_label")}
          style={{ fontSize: 12, lineHeight: 1, padding: 0, cursor: "pointer" }}
        >
          ?
          <VisuallyHidden>
            {t("kp.booking.status_help_open_label")}
          </VisuallyHidden>
        </UnstyledButton>
      </Tooltip>

      <Modal
        opened={opened}
        onClose={close}
        title={t("kp.booking.status_help_title")}
        centered
      >
        <Stack gap="sm">
          <Text size="sm" c="dimmed">
            {t("kp.booking.status_help_description")}
          </Text>
          {BOOKING_STATUSES.map((status) => (
            <Stack key={status} gap={4}>
              <KpBookingStatusBadge
                status={status}
                style={{ minWidth: 120, justifyContent: "center" }}
              />
              <Text size="sm" c="dimmed">
                {t(`kp.booking.statuses.${status.toLowerCase()}.description`)}
              </Text>
            </Stack>
          ))}
        </Stack>
      </Modal>
    </>
  );
};
export default KpBookingStatusHelp;
