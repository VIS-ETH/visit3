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
import { notifications } from "@mantine/notifications";
import { IconAlertCircle, IconDownload } from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router";
import BackButton from "../components/BackButton";
import { KpBookingStatusBadge } from "../components/KpBookingStatusBadge";
import {
  KpBookingStatus,
  KpCompanyLanguage,
  KpEventServiceRequirementType,
  type KpCompanyLanguage as KpCompanyLanguageType,
  type RequirementFileResponse,
  type ServiceRequirementResponse,
} from "../orval/generated/fastAPI.schemas";
import {
  getGetEventBookingQueryKey,
  getListEventBookingsQueryKey,
  getStaffBookingRequirementFileDownloadUrl,
  useListStaffBookingRequirementFiles,
  useConfirmBooking,
  useGetEventBooking,
} from "../orval/generated/kp/kp";
import { formatPrice } from "../utils/price-utils";

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

const getLanguageLabelKey = (language: KpCompanyLanguageType) => {
  switch (language) {
    case KpCompanyLanguage.ENGLISH:
      return "kp.booking_booklet_details.language_ENGLISH";
    case KpCompanyLanguage.GERMAN:
      return "kp.booking_booklet_details.language_GERMAN";
    case KpCompanyLanguage.FRENCH:
      return "kp.booking_booklet_details.language_FRENCH";
    case KpCompanyLanguage.ITALIAN:
      return "kp.booking_booklet_details.language_ITALIAN";
  }
};

const StaffRequirementRow = ({
  bookingServiceId,
  isChecking,
  requirementFile,
  requirement,
}: {
  bookingServiceId: string;
  isChecking: boolean;
  requirementFile?: RequirementFileResponse;
  requirement: ServiceRequirementResponse;
}) => {
  const { t } = useTranslation();
  const [isDownloading, setIsDownloading] = useState(false);
  const isTextRequirement = requirement.type === KpEventServiceRequirementType.text;
  const requirementTypeLabels: Record<KpEventServiceRequirementType, string> = {
    [KpEventServiceRequirementType.text]: t("kp.booking.requirement_type_text"),
    [KpEventServiceRequirementType.file]: t("kp.booking.requirement_type_file"),
    [KpEventServiceRequirementType.image]: t("kp.booking.requirement_type_image"),
    [KpEventServiceRequirementType.pdf]: t("kp.booking.requirement_type_pdf"),
    [KpEventServiceRequirementType.pdf_single_page]: t("kp.booking.requirement_type_pdf_single_page"),
    [KpEventServiceRequirementType.video]: t("kp.booking.requirement_type_video"),
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
    } catch {
      notifications.show({
        color: "red",
        message: t("kp.booking.requirement_download_error"),
      });
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
            t("kp.manage.booking_requirement_missing")}
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
        <Badge color={isChecking ? "gray" : "yellow"} variant="light">
          {isChecking
            ? t("kp.manage.booking_requirement_checking")
            : t("kp.manage.booking_requirement_missing_badge")}
        </Badge>
      )}
    </Group>
  );
};

const KpBookingDetails = () => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { id, bookingId } = useParams<{ id: string; bookingId: string }>();
  const backToBookings = id ? `/kp/${id}?tab=bookings` : "/kp";
  const {
    data: booking,
    isError,
    isLoading,
  } = useGetEventBooking(id ?? "", bookingId ?? "", {
    query: { enabled: Boolean(id && bookingId) },
  });
  const { data: requirementFiles, isLoading: isRequirementFilesLoading } =
    useListStaffBookingRequirementFiles(id ?? "", bookingId ?? "", {
      query: { enabled: Boolean(id && bookingId) },
    });
  const { mutate: confirmBooking, isPending: isConfirming } = useConfirmBooking(
    {
      mutation: {
        onSuccess: async () => {
          await Promise.all([
            queryClient.invalidateQueries({
              queryKey: getGetEventBookingQueryKey(id, bookingId),
            }),
            queryClient.invalidateQueries({
              queryKey: getListEventBookingsQueryKey(id),
            }),
          ]);
          notifications.show({
            color: "green",
            message: t("kp.manage.booking_confirmed"),
          });
        },
        onError: () => {
          notifications.show({
            color: "red",
            message: t("kp.manage.booking_confirm_error"),
          });
        },
      },
    },
  );

  const canConfirm = booking?.status === KpBookingStatus.FINALIZED;

  const handleConfirmBooking = () => {
    if (!bookingId || !confirm(t("kp.manage.booking_confirm_prompt"))) return;
    confirmBooking({ bookingId });
  };

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
        <Alert icon={<IconAlertCircle />} color="red">
          {t("kp.manage.booking_detail_not_found")}
        </Alert>
      </Stack>
    );
  }

  const bookingServices = booking.services ?? [];
  const companyDetails = booking.company_details;
  const yesNo = (value: boolean) => (value ? t("common.yes") : t("common.no"));
  const languageLabels =
    companyDetails?.languages.map((language) =>
      t(getLanguageLabelKey(language)),
    ) ?? [];
  const industryLabels =
    companyDetails?.industries?.map((industry) => industry.name) ?? [];

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
        <Group gap="sm">
          <KpBookingStatusBadge status={booking.status} />
          {canConfirm ? (
            <Button
              color="green"
              loading={isConfirming}
              onClick={handleConfirmBooking}
            >
              {t("kp.manage.booking_confirm")}
            </Button>
          ) : null}
        </Group>
      </Group>

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
              value={`CHF ${formatPrice(booking.total_price)}`}
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

      <Paper withBorder p="lg" radius="md">
        <Stack gap="lg">
          <Title order={4}>{t("kp.manage.booking_detail_completion")}</Title>
          <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="lg">
            <DetailField
              label={t("kp.manage.booking_details")}
              value={
                <Badge
                  color={booking.company_details_submitted ? "green" : "gray"}
                  variant="light"
                >
                  {booking.company_details_submitted
                    ? t("kp.manage.booking_details_submitted")
                    : t("kp.manage.booking_details_missing")}
                </Badge>
              }
            />
            <DetailField
              label={t("kp.manage.booking_status")}
              value={<KpBookingStatusBadge status={booking.status} />}
            />
          </SimpleGrid>
        </Stack>
      </Paper>

      {companyDetails ? (
        <Paper withBorder p="lg" radius="md">
          <Stack gap="lg">
            <Title order={4}>{t("kp.manage.booking_booklet_details_title")}</Title>
            <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} spacing="lg">
              <DetailField
                label={t("kp.booking_booklet_details.brand_name")}
                value={companyDetails.brand_name}
              />
              <DetailField
                label={t("kp.booking_booklet_details.contact_person")}
                value={companyDetails.contact_person}
              />
              <DetailField
                label={t("kp.booking_booklet_details.employees_count")}
                value={companyDetails.employees_count ?? "-"}
              />
              <DetailField
                label={t("kp.booking_booklet_details.employees_count_switzerland")}
                value={companyDetails.employees_count_switzerland ?? "-"}
              />
              <DetailField
                label={t("kp.booking_booklet_details.languages")}
                value={languageLabels.length > 0 ? languageLabels.join(", ") : "-"}
              />
              <DetailField
                label={t("kp.booking_booklet_details.industries")}
                value={industryLabels.length > 0 ? industryLabels.join(", ") : "-"}
              />
              <DetailField
                label={t("kp.booking_booklet_details.offer_internship")}
                value={yesNo(companyDetails.offer_internship)}
              />
              <DetailField
                label={t("kp.booking_booklet_details.offer_part_time")}
                value={yesNo(companyDetails.offer_part_time)}
              />
              <DetailField
                label={t("kp.booking_booklet_details.offer_thesis")}
                value={yesNo(companyDetails.offer_thesis)}
              />
            </SimpleGrid>
            <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg">
              <DetailField
                label={t("kp.booking_booklet_details.address")}
                value={
                  <Text fw={500} style={{ whiteSpace: "pre-wrap" }}>
                    {companyDetails.address}
                  </Text>
                }
              />
              <DetailField
                label={t("kp.booking_booklet_details.places_of_work")}
                value={
                  <Text fw={500} style={{ whiteSpace: "pre-wrap" }}>
                    {companyDetails.places_of_work}
                  </Text>
                }
              />
            </SimpleGrid>
            <DetailField
              label={t("kp.booking_booklet_details.profile")}
              value={
                <Text fw={500} style={{ whiteSpace: "pre-wrap" }}>
                  {companyDetails.profile}
                </Text>
              }
            />
          </Stack>
        </Paper>
      ) : null}

      <Paper withBorder p="lg" radius="md">
        <Stack gap="md">
          <Title order={4}>{t("kp.manage.booking_services")}</Title>
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
                      {bookingService.service.requirements.map((requirement) => (
                        <StaffRequirementRow
                          bookingServiceId={bookingService.id}
                          isChecking={isRequirementFilesLoading}
                          key={requirement.id}
                          requirementFile={requirementFiles?.files[requirement.id]}
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
    </Stack>
  );
};

export default KpBookingDetails;
