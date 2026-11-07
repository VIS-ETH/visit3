import { Alert, Button, Group, Stack, Text, Title } from "@mantine/core";
import { IconDeviceFloppy, IconProgressCheck } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import type { BookingServiceResponse } from "../../../orval/generated/fastAPI.schemas";
import BookedServiceCard from "./BookedServiceCard";
import RequirementsBadge from "./RequirementsBadge";
import { requirementChangeKey } from "./requirement-changes";
import type { RequirementChanges } from "./use-requirement-changes";

const RequirementsSection = ({
  bookingServices,
  changes,
  editable,
  listedServices,
  onSave,
}: {
  bookingServices: BookingServiceResponse[];
  changes: RequirementChanges;
  editable: boolean;
  listedServices: BookingServiceResponse[];
  onSave: () => void;
}) => {
  const { t } = useTranslation();
  const requirementKeys = bookingServices.flatMap((bookingService) =>
    bookingService.service.requirements.map((requirement) =>
      requirementChangeKey(bookingService.id, requirement.id),
    ),
  );
  const completedCount = requirementKeys.filter(
    (key) => changes.completion[key],
  ).length;

  return (
    <Stack gap="md">
      <Group justify="space-between" align="flex-start">
        <div>
          <Title order={4}>{t("kp.booking_manage.requirements_title")}</Title>
          <Text c="dimmed" size="sm">
            {t("kp.booking_manage.requirements_description")}
          </Text>
        </div>
        <RequirementsBadge
          completed={completedCount}
          total={requirementKeys.length}
        />
      </Group>
      {completedCount < requirementKeys.length ? (
        <Alert icon={<IconProgressCheck />} color="yellow">
          {t("kp.booking_manage.incomplete_requirements_notice")}
        </Alert>
      ) : null}
      {editable ? (
        <Group justify="flex-end">
          <Button
            leftSection={<IconDeviceFloppy size={16} />}
            disabled={changes.changeList.length === 0}
            loading={changes.isSaving}
            onClick={onSave}
          >
            {t("kp.booking_manage.save_requirement_changes", {
              count: changes.changeList.length,
            })}
          </Button>
        </Group>
      ) : null}
      {bookingServices.length ? (
        <Stack gap="sm">
          {listedServices.map((bookingService) => (
            <BookedServiceCard
              bookingService={bookingService}
              changes={changes}
              editable={editable}
              key={bookingService.id}
            />
          ))}
        </Stack>
      ) : (
        <Text c="dimmed" size="sm">
          {t("kp.booking_manage.no_services")}
        </Text>
      )}
    </Stack>
  );
};

export default RequirementsSection;
