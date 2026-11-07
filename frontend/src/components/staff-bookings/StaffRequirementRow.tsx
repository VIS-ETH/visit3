import { Badge, Button, Group, Stack, Text } from "@mantine/core";
import { IconDownload } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import {
  KpEventServiceRequirementType,
  type RequirementFileResponse,
  type ServiceRequirementResponse,
} from "../../orval/generated/fastAPI.schemas";
import { getStaffBookingRequirementFileDownloadUrl } from "../../orval/generated/kp/kp";
import { useAsyncAction } from "../../hooks/use-async-action";
import { requirementTypeLabel } from "../../utils/requirement-type";

const StaffRequirementRow = ({
  bookingServiceId,
  hasLoadError,
  isChecking,
  requirementFile,
  requirement,
}: {
  bookingServiceId: string;
  hasLoadError: boolean;
  isChecking: boolean;
  requirementFile?: RequirementFileResponse;
  requirement: ServiceRequirementResponse;
}) => {
  const { t } = useTranslation();
  const { run: download, isRunning: isDownloading } = useAsyncAction(
    async () => {
      const response = await getStaffBookingRequirementFileDownloadUrl(
        bookingServiceId,
        requirement.id,
      );
      window.location.assign(response.url);
    },
  );

  if (requirement.type === KpEventServiceRequirementType.text) {
    return null;
  }

  return (
    <Group justify="space-between" align="center" wrap="nowrap">
      <Stack gap={2}>
        <Group gap="xs">
          <Text fw={500} size="sm">
            {requirement.name}
          </Text>
          <Badge variant="light" size="sm">
            {requirementTypeLabel(requirement.type, t)}
          </Badge>
        </Group>
        <Text c="dimmed" size="xs">
          {requirementFile?.stored_file.original_filename ??
            (hasLoadError
              ? t("kp.manage.booking_requirement_load_error")
              : t("kp.manage.booking_requirement_missing"))}
        </Text>
      </Stack>
      {requirementFile ? (
        <Button
          leftSection={<IconDownload size={16} />}
          loading={isDownloading}
          onClick={() => {
            void download();
          }}
          size="xs"
          variant="light"
        >
          {t("kp.manage.booking_requirement_download")}
        </Button>
      ) : (
        <Badge
          color={hasLoadError ? "red" : isChecking ? "gray" : "yellow"}
          variant="light"
        >
          {hasLoadError
            ? t("kp.manage.booking_requirement_load_error_badge")
            : isChecking
              ? t("kp.manage.booking_requirement_checking")
              : t("kp.manage.booking_requirement_missing_badge")}
        </Badge>
      )}
    </Group>
  );
};

export default StaffRequirementRow;
