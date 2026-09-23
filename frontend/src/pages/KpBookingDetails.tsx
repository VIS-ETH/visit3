import {
  Alert,
  Badge,
  Button,
  Center,
  Divider,
  Group,
  Loader,
  Paper,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import {
  IconAlertCircle,
  IconDownload,
  IconRefresh,
} from "@tabler/icons-react";
import { useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router";
import BackButton from "../components/BackButton";
import { KpBookingStatusBadge } from "../components/KpBookingStatusBadge";
import BookingActionBar from "../components/bookings/BookingActionBar";
import BookingCompletenessCard from "../components/bookings/BookingCompletenessCard";
import BookingEditPanel from "../components/bookings/BookingEditPanel";
import BookingNametagsCard from "../components/bookings/BookingNametagsCard";
import BookingWaitlistCard from "../components/bookings/BookingWaitlistCard";
import BookingStatusTimeline from "../components/bookings/BookingStatusTimeline";
import VenueMapViewer from "../components/venue/VenueMapViewer";
import {
  KpEventServiceRequirementType,
  type RequirementFileResponse,
  type ServiceRequirementResponse,
} from "../orval/generated/fastAPI.schemas";
import {
  getStaffBookingRequirementFileDownloadUrl,
  useListStaffBookingRequirementFiles,
  useGetEventBooking,
} from "../orval/generated/kp/kp";
import { formatPrice } from "../utils/price-utils";
import { getApiErrorCode } from "../api/errors";

const NOT_ALLOWED_CODE = "error.not_allowed";

const DetailField = ({ label, value }: { label: string; value: ReactNode }) => (
  <Stack gap={2}>
    <Text c="dimmed" size="sm">
      {label}
    </Text>
    {typeof value === "string" || typeof value === "number" ? (
      <Text fw={500}>{value}</Text>
    ) : (
      value
    )}
  </Stack>
);

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
  const [isDownloading, setIsDownloading] = useState(false);
  const isTextRequirement =
    requirement.type === KpEventServiceRequirementType.text;
  const requirementTypeLabels: Record<KpEventServiceRequirementType, string> = {
    [KpEventServiceRequirementType.text]: t("kp.booking.requirement_type_text"),
    [KpEventServiceRequirementType.file]: t("kp.booking.requirement_type_file"),
    [KpEventServiceRequirementType.image]: t(
      "kp.booking.requirement_type_image",
    ),
    [KpEventServiceRequirementType.pdf]: t("kp.booking.requirement_type_pdf"),
    [KpEventServiceRequirementType.video]: t(
      "kp.booking.requirement_type_video",
    ),
  };

  const handleDownload = async () => {
    if (!requirementFile) return;
    setIsDownloading(true);
    try {
      const response = await getStaffBookingRequirementFileDownloadUrl(
        bookingServiceId,
        requirement.id,
      );
      window.open(response.url, "_blank", "noopener,noreferrer");
    } finally {
      setIsDownloading(false);
    }
  };

  if (isTextRequirement) {
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
            {requirementTypeLabels[requirement.type]}
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
          onClick={handleDownload}
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

const KpBookingDetails = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { id, bookingId } = useParams<{ id: string; bookingId: string }>();
  const backToBookings = id ? `/kp/${id}?tab=bookings` : "/kp";
  const {
    data: booking,
    error,
    isError,
    isLoading,
  } = useGetEventBooking(id ?? "", bookingId ?? "", {
    query: { enabled: Boolean(id && bookingId), retry: false },
  });
  const isForbidden = getApiErrorCode(error) === NOT_ALLOWED_CODE;
  const {
    data: requirementFiles,
    isLoading: isRequirementFilesLoading,
    isError: isRequirementFilesError,
    refetch: refetchRequirementFiles,
  } = useListStaffBookingRequirementFiles(id ?? "", bookingId ?? "", {
    query: { enabled: Boolean(id && bookingId), retry: false },
  });

  if (!id || !bookingId) {
    return (
      <Stack gap="md">
        <BackButton to="/kp" />
        <Alert icon={<IconAlertCircle />} color="red">
          {t("kp.manage.booking_detail_not_found")}
        </Alert>
      </Stack>
    );
  }

  if (isLoading) {
    return (
      <Stack gap="md">
        <BackButton to={backToBookings} />
        <Center py="xl">
          <Loader />
        </Center>
      </Stack>
    );
  }

  if (isError || !booking) {
    return (
      <Stack gap="md">
        <BackButton to={backToBookings} />
        <Alert
          icon={<IconAlertCircle />}
          color={isForbidden ? "yellow" : "red"}
          title={isForbidden ? t("not_allowed.title") : undefined}
        >
          {isForbidden
            ? t("kp.manage.booking_detail_forbidden")
            : t("kp.manage.booking_detail_not_found")}
        </Alert>
      </Stack>
    );
  }

  const bookingServices = booking.services ?? [];

  return (
    <Stack gap="md">
      <BackButton to={backToBookings} />

      <Group justify="space-between" align="flex-start">
        <div>
          <Title order={2}>
            {t("kp.manage.booking_detail_title", {
              bookingNumber: booking.booking_number,
            })}
          </Title>
          <Text c="dimmed" size="sm">
            {booking.company.name}
          </Text>
        </div>
        <KpBookingStatusBadge size="lg" status={booking.status} />
      </Group>

      <Paper withBorder p="lg" radius="md">
        <Stack gap="lg">
          <Title order={4}>{t("kp.manage.booking_timeline_title")}</Title>
          <BookingStatusTimeline booking={booking} />
        </Stack>
      </Paper>

      <BookingActionBar
        booking={booking}
        eventId={id}
        onDeleted={() => {
          void navigate(backToBookings);
        }}
      />

      <BookingCompletenessCard booking={booking} />

      <BookingEditPanel booking={booking} eventId={id} />

      <BookingWaitlistCard booking={booking} />

      <Paper withBorder p="lg" radius="md">
        <Stack gap="lg">
          <Title order={4}>{t("kp.manage.booking_detail_overview")}</Title>
          <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} spacing="lg">
            <DetailField
              label={t("kp.manage.booking_company")}
              value={booking.company.name}
            />
            <DetailField
              label={t("kp.manage.booking_booth_zone")}
              value={booking.booth_zone.name}
            />
            <DetailField
              label={t("kp.manage.booking_booth_nr")}
              value={booking.booth_nr ?? "-"}
            />
            <DetailField
              label={t("kp.manage.booking_total")}
              value={`CHF ${formatPrice(booking.net_total)}`}
            />
            <DetailField
              label={t("kp.manage.booking_gross_total")}
              value={`CHF ${formatPrice(booking.price.gross)}`}
            />
            <DetailField
              label={t("kp.manage.booking_nametags")}
              value={booking.nametag_count}
            />
            <DetailField
              label={t("kp.manage.booking_waitlist")}
              value={booking.waitlist_count}
            />
          </SimpleGrid>
        </Stack>
      </Paper>

      <BookingNametagsCard bookingId={booking.id} />

      <Paper withBorder p="lg" radius="md">
        <Stack gap="md">
          <Title order={4}>{t("kp.venue.booking_map_title")}</Title>
          <VenueMapViewer
            eventId={id}
            highlightBooth={{
              zoneId: booking.booth_zone_id,
              boothNr: booking.booth_nr,
            }}
            selectedZoneId={booking.booth_zone_id}
          />
        </Stack>
      </Paper>

      <Paper withBorder p="lg" radius="md">
        <Stack gap="md">
          <Title order={4}>{t("kp.manage.booking_services")}</Title>
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
                    <Badge variant="light">
                      {t("kp.manage.booking_service_quantity", {
                        quantity: bookingService.quantity,
                      })}
                    </Badge>
                  </Group>

                  {bookingService.service.requirements.some(
                    (requirement) =>
                      requirement.type !== KpEventServiceRequirementType.text,
                  ) ? (
                    <Stack gap="xs">
                      <Text c="dimmed" fw={500} size="sm">
                        {t("kp.manage.booking_service_requirements")}
                      </Text>
                      {bookingService.service.requirements.map(
                        (requirement) => (
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
                        ),
                      )}
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
    </Stack>
  );
};

export default KpBookingDetails;
