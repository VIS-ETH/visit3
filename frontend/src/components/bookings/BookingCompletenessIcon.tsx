import { List, Stack, Text, ThemeIcon, Tooltip } from "@mantine/core";
import { IconAlertTriangle, IconCheck } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import type { BookingServiceResponse } from "../../orval/generated/fastAPI.schemas";
import { useMissingItemLabel } from "./missing-items";

const BookingCompletenessIcon = ({
  isComplete,
  missingItems,
  services,
}: {
  isComplete: boolean;
  missingItems: string[];
  services: BookingServiceResponse[];
}) => {
  const { t } = useTranslation();
  const missingItemLabel = useMissingItemLabel(services);

  if (isComplete) {
    return (
      <Tooltip label={t("kp.manage.booking_complete")}>
        <ThemeIcon
          aria-label={t("kp.manage.booking_complete")}
          color="green"
          radius="xl"
          size="sm"
          variant="light"
        >
          <IconCheck size={14} />
        </ThemeIcon>
      </Tooltip>
    );
  }

  return (
    <Tooltip
      label={
        <Stack gap={2}>
          <Text size="xs">{t("kp.manage.booking_incomplete")}</Text>
          <List size="xs" withPadding>
            {missingItems.map((item) => (
              <List.Item key={item}>{missingItemLabel(item)}</List.Item>
            ))}
          </List>
        </Stack>
      }
      multiline
      w={260}
    >
      <ThemeIcon
        aria-label={t("kp.manage.booking_incomplete")}
        color="yellow"
        radius="xl"
        size="sm"
        variant="light"
      >
        <IconAlertTriangle size={14} />
      </ThemeIcon>
    </Tooltip>
  );
};

export default BookingCompletenessIcon;
