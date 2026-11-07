import {
  Alert,
  Badge,
  Button,
  Divider,
  Group,
  Paper,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import {
  IconAlertCircle,
  IconEyeCheck,
  IconRefresh,
} from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import {
  KpEventServiceRequirementType,
  type StaffBookingResponse,
} from "../../orval/generated/fastAPI.schemas";
import { useListStaffBookingRequirementFiles } from "../../orval/generated/kp/kp";
import { useAsyncAction } from "../../hooks/use-async-action";
import {
  addedQuantityByBookingServiceId,
  hasNewAdditions,
} from "../../utils/booking-status";
import StaffRequirementRow from "./StaffRequirementRow";
import { useBookingActions } from "./useBookingActions";

const BookingServicesCard = ({
  booking,
  eventId,
}: {
  booking: StaffBookingResponse;
  eventId: string;
}) => {
  const { t } = useTranslation();
  const actions = useBookingActions(eventId);
  const { run: acknowledge, isRunning: isAcknowledging } = useAsyncAction(() =>
    actions.acknowledgeAdditions(booking.id),
  );
  const {
    data: requirementFiles,
    isLoading: isRequirementFilesLoading,
    isError: isRequirementFilesError,
    refetch: refetchRequirementFiles,
  } = useListStaffBookingRequirementFiles(eventId, booking.id, {
    query: { retry: false },
  });
  const bookingServices = booking.services ?? [];
  const addedQuantities = addedQuantityByBookingServiceId(booking);

  return (
    <Paper withBorder p="lg" radius="md">
      <Stack gap="md">
        <Group justify="space-between" align="center">
          <Title order={4}>{t("kp.manage.booking_services")}</Title>
          {hasNewAdditions(booking) ? (
            <Button
              color="gray"
              leftSection={<IconEyeCheck size={16} />}
              loading={isAcknowledging}
              onClick={() => {
                void acknowledge();
              }}
              size="xs"
              variant="subtle"
            >
              {t("kp.manage.booking_additions_acknowledge")}
            </Button>
          ) : null}
        </Group>
        {isRequirementFilesError ? (
          <Alert icon={<IconAlertCircle />} color="red">
            <Group justify="space-between" align="center" wrap="nowrap">
              <Text size="sm">
                {t("kp.manage.booking_requirement_load_error")}
              </Text>
              <Button
                leftSection={<IconRefresh size={16} />}
                onClick={() => {
                  void refetchRequirementFiles();
                }}
                size="xs"
                variant="light"
              >
                {t("kp.manage.booking_requirement_retry")}
              </Button>
            </Group>
          </Alert>
        ) : null}
        {bookingServices.length > 0 ? (
          <Stack gap="md">
            {bookingServices.map((bookingService, index) => (
              <Stack gap="sm" key={bookingService.id}>
                {index > 0 ? <Divider /> : null}
                <Group justify="space-between" align="flex-start">
                  <Stack gap={2}>
                    <Text fw={600}>{bookingService.service.name}</Text>
                    {bookingService.service.description ? (
                      <Text c="dimmed" size="sm">
                        {bookingService.service.description}
                      </Text>
                    ) : null}
                  </Stack>
                  <Group gap="xs" wrap="nowrap">
                    {addedQuantities.has(bookingService.id) ? (
                      <Badge color="orange" variant="dot">
                        {t("kp.manage.booking_service_added", {
                          quantity: addedQuantities.get(bookingService.id),
                        })}
                      </Badge>
                    ) : null}
                    <Badge variant="light">
                      {t("kp.manage.booking_service_quantity", {
                        quantity: bookingService.quantity,
                      })}
                    </Badge>
                  </Group>
                </Group>

                {bookingService.service.requirements.some(
                  (requirement) =>
                    requirement.type !== KpEventServiceRequirementType.text,
                ) ? (
                  <Stack gap="xs">
                    <Text c="dimmed" fw={500} size="sm">
                      {t("kp.manage.booking_service_requirements")}
                    </Text>
                    {bookingService.service.requirements.map((requirement) => (
                      <StaffRequirementRow
                        bookingServiceId={bookingService.id}
                        hasLoadError={isRequirementFilesError}
                        isChecking={isRequirementFilesLoading}
                        key={requirement.id}
                        requirementFile={
                          requirementFiles?.files[requirement.id]
                        }
                        requirement={requirement}
                      />
                    ))}
                  </Stack>
                ) : null}
              </Stack>
            ))}
          </Stack>
        ) : (
          <Text c="dimmed">{t("kp.manage.booking_services_empty")}</Text>
        )}
      </Stack>
    </Paper>
  );
};

export default BookingServicesCard;
