import { Badge, Card, Group, Stack, Text } from "@mantine/core";
import { useTranslation } from "react-i18next";
import type { BookingServiceResponse } from "../../../orval/generated/fastAPI.schemas";
import RequirementEditor from "./RequirementEditor";
import RequirementsBadge from "./RequirementsBadge";
import { requirementChangeKey } from "./requirement-changes";
import type { RequirementChanges } from "./use-requirement-changes";

const BookedServiceCard = ({
  bookingService,
  changes,
  editable,
}: {
  bookingService: BookingServiceResponse;
  changes: RequirementChanges;
  editable: boolean;
}) => {
  const { t } = useTranslation();
  const requirements = bookingService.service.requirements
    .slice()
    .sort((a, b) => a.order - b.order);
  const keyOf = (requirementId: string) =>
    requirementChangeKey(bookingService.id, requirementId);
  const completedRequirements = requirements.filter(
    (requirement) => changes.completion[keyOf(requirement.id)],
  ).length;

  return (
    <Card withBorder radius="md" p="lg">
      <Stack gap="md">
        <Group justify="space-between" align="flex-start">
          <div>
            <Group gap="xs">
              <Text fw={600}>{bookingService.service.name}</Text>
              <Badge variant="light">x{bookingService.quantity}</Badge>
              {bookingService.included_quantity > 0 ? (
                <Badge color="green" variant="light">
                  {t("kp.booking.service_included_note", {
                    included: bookingService.included_quantity,
                  })}
                </Badge>
              ) : null}
            </Group>
            {bookingService.service.description ? (
              <Text c="dimmed" size="sm">
                {bookingService.service.description}
              </Text>
            ) : null}
          </div>
          <RequirementsBadge
            completed={completedRequirements}
            total={requirements.length}
          />
        </Group>
        {requirements.length ? (
          <Stack gap={0}>
            {requirements.map((requirement) => (
              <RequirementEditor
                bookingServiceId={bookingService.id}
                editable={editable && !changes.isSaving}
                isSaving={changes.savingKey === keyOf(requirement.id)}
                key={requirement.id}
                onChange={changes.setChange}
                onCompletionChange={changes.setCompletionFor}
                pendingChange={changes.pendingChanges[keyOf(requirement.id)]}
                requirement={requirement}
                serviceName={bookingService.service.name}
              />
            ))}
          </Stack>
        ) : null}
      </Stack>
    </Card>
  );
};

export default BookedServiceCard;
