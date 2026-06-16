import {
  Alert,
  Badge,
  Button,
  Center,
  Checkbox,
  FileInput,
  Group,
  Loader,
  MultiSelect,
  NumberInput,
  Paper,
  SimpleGrid,
  Stack,
  Text,
  Textarea,
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  IconAlertCircle,
  IconDeviceFloppy,
  IconDownload,
  IconTrash,
  IconUpload,
} from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router";
import BackButton from "../components/BackButton";
import {
  KpBookingStatus,
  KpCompanyLanguage,
  KpEventServiceRequirementType,
  type BookingResponse,
  type KpCompanyLanguage as KpCompanyLanguageType,
} from "../orval/generated/fastAPI.schemas";
import {
  getBookingRequirementFileDownloadUrl,
  getGetBookingCompanyDetailsQueryKey,
  getGetBookingRequirementFileQueryKey,
  getGetMyBookingQueryKey,
  useDeleteBookingLogo,
  useDeleteBookingRequirementFile,
  useGetBookingCompanyDetails,
  useGetBookingRequirementFile,
  useGetKpById,
  useGetMyBooking,
  useListIndustries,
  useUploadBookingLogo,
  useUploadBookingRequirementFile,
  useUpsertBookingCompanyDetails,
} from "../orval/generated/kp/kp";
import {
  bookingCompanyDetailsSchema,
  type BookingCompanyDetailsFormValues,
} from "../schemas/kpSchema";
import { useTranslatedForm } from "../utils/translator";

const emptyValues: BookingCompanyDetailsFormValues = {
  brandName: "",
  profile: "",
  address: "",
  contactPerson: "",
  placesOfWork: "",
  website: "",
  employeesCount: 0,
  employeesCountSwitzerland: 0,
  vacanciesWorldwide: 0,
  vacanciesSwitzerland: 0,
  annualRevenueChfMillions: 0,
  offerInternship: false,
  offerPartTime: false,
  offerThesis: false,
  languages: [],
  industryIds: [],
};

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

const KpBookingBookletDetails = () => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { id = "", bookingId = "" } = useParams<{
    id: string;
    bookingId: string;
  }>();
  const eventId = id.trim();
  const normalizedBookingId = bookingId.trim();

  const form = useTranslatedForm<typeof bookingCompanyDetailsSchema>(
    bookingCompanyDetailsSchema,
    {
      initialValues: emptyValues,
      validateInputOnChange: true,
    },
  );

  const {
    data: event,
    isLoading: isLoadingEvent,
    isError: isEventError,
  } = useGetKpById(eventId, {
    query: { enabled: Boolean(eventId) },
  });
  const {
    data: booking,
    isLoading: isLoadingBooking,
    isError: isBookingError,
  } = useGetMyBooking(eventId, {
    query: { enabled: Boolean(eventId) },
  });
  const {
    data: details,
    isLoading: isLoadingDetails,
    isError: isDetailsError,
  } = useGetBookingCompanyDetails(booking?.id ?? "", {
    query: { enabled: Boolean(booking?.id) },
  });
  const { data: industries = [] } = useListIndustries();

  const { mutateAsync: saveDetails, isPending: isSaving } =
    useUpsertBookingCompanyDetails();
  const { clearErrors, resetDirty, setInitialValues, setValues } = form;

  const bookletDetailsValues = useMemo<BookingCompanyDetailsFormValues>(
    () =>
      details
        ? {
            brandName: details.brand_name,
            profile: details.profile,
            address: details.address,
            contactPerson: details.contact_person,
            placesOfWork: details.places_of_work,
            website: details.website,
            employeesCount: details.employees_count ?? 0,
            employeesCountSwitzerland:
              details.employees_count_switzerland ?? 0,
            vacanciesWorldwide: details.vacancies_worldwide ?? 0,
            vacanciesSwitzerland: details.vacancies_switzerland ?? 0,
            annualRevenueChfMillions:
              details.annual_revenue_chf_millions ?? 0,
            offerInternship: details.offer_internship,
            offerPartTime: details.offer_part_time,
            offerThesis: details.offer_thesis,
            languages: details.languages,
            industryIds: details.industry_ids ?? [],
          }
        : emptyValues,
    [details],
  );

  const [hasSetInitialValues, setHasSetInitialValues] = useState(false);

  useEffect(() => {
    if (hasSetInitialValues || isLoadingDetails) return;
    setInitialValues(bookletDetailsValues);
    setValues(bookletDetailsValues);
    resetDirty(bookletDetailsValues);
    clearErrors();
    setHasSetInitialValues(true);
  }, [
    booking?.id,
    clearErrors,
    bookletDetailsValues,
    isLoadingDetails,
    resetDirty,
    setInitialValues,
    setValues,
    hasSetInitialValues,
  ]);

  const isLoading =
    isLoadingEvent || isLoadingBooking || isLoadingDetails;

  if (isLoading) {
    return (
      <Center py="xl">
        <Loader />
      </Center>
    );
  }

  if (
    !eventId ||
    !normalizedBookingId ||
    isEventError ||
    isBookingError ||
    isDetailsError ||
    !event ||
    booking?.id !== normalizedBookingId
  ) {
    return (
      <Stack gap="md">
        <BackButton to={eventId ? `/kp/${eventId}` : "/kp"} />
        <Alert icon={<IconAlertCircle />} color="red" title={t("server.error")}>
          {t("kp.booking.error")}
        </Alert>
      </Stack>
    );
  }

  const isEditable =
    booking.status !== KpBookingStatus.CONFIRMED &&
    booking.status !== KpBookingStatus.CANCELLED;
  const languageOptions = Object.values(KpCompanyLanguage).map((language) => ({
    value: language,
    label: t(getLanguageLabelKey(language)),
  }));
  const industryOptions = industries.map((industry) => ({
    value: industry.id,
    label: industry.name,
  }));

  const handleSubmit = async (values: BookingCompanyDetailsFormValues) => {
    try {
      await saveDetails({
        bookingId: booking.id,
        data: {
          brand_name: values.brandName.trim(),
          profile: values.profile.trim(),
          address: values.address.trim(),
          contact_person: values.contactPerson.trim(),
          places_of_work: values.placesOfWork.trim(),
          website: values.website.trim(),
          employees_count: values.employeesCount,
          employees_count_switzerland: values.employeesCountSwitzerland,
          vacancies_worldwide: values.vacanciesWorldwide,
          vacancies_switzerland: values.vacanciesSwitzerland,
          annual_revenue_chf_millions: values.annualRevenueChfMillions,
          offer_internship: values.offerInternship,
          offer_part_time: values.offerPartTime,
          offer_thesis: values.offerThesis,
          languages: values.languages,
          industry_ids: values.industryIds,
        },
      });

      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: getGetBookingCompanyDetailsQueryKey(booking.id),
        }),
        queryClient.invalidateQueries({
          queryKey: getGetMyBookingQueryKey(eventId),
        }),
      ]);
      resetDirty(values);
      notifications.show({
        color: "green",
        message: t("kp.booking_booklet_details.saved"),
      });
    } catch {
      notifications.show({
        color: "red",
        message: t("kp.booking_booklet_details.save_error"),
      });
    }
  };

  return (
    <Stack gap="md">
      <BackButton to={`/kp/${eventId}/booking/${booking.id}/manage`} />
      <div>
        <Title order={2}>{t("kp.booking_booklet_details.title")}</Title>
        <Text c="dimmed" size="sm">
          {t("kp.booking_manage.services_page_subtitle", {
            eventName: event.name,
            bookingNumber: booking.booking_number,
          })}
        </Text>
      </div>

      {!isEditable ? (
        <Alert icon={<IconAlertCircle />} color="yellow">
          {t("kp.booking_manage.readonly_notice_booklet_details")}
        </Alert>
      ) : null}

      <form onSubmit={form.onSubmit(handleSubmit)}>
        <Paper withBorder p="lg" radius="md">
          <Stack gap="lg">
            <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
              <TextInput
                label={t("kp.booking_booklet_details.brand_name")}
                disabled={!isEditable || isSaving}
                {...form.getInputProps("brandName")}
              />
              <TextInput
                label={t("kp.booking_booklet_details.contact_person")}
                disabled={!isEditable || isSaving}
                {...form.getInputProps("contactPerson")}
              />
            </SimpleGrid>

            <Textarea
              label={t("kp.booking_booklet_details.profile")}
              minRows={8}
              autosize
              disabled={!isEditable || isSaving}
              {...form.getInputProps("profile")}
            />

            <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
              <Textarea
                label={t("kp.booking_booklet_details.address")}
                minRows={4}
                autosize
                disabled={!isEditable || isSaving}
                {...form.getInputProps("address")}
              />
              <Textarea
                label={t("kp.booking_booklet_details.places_of_work")}
                minRows={4}
                autosize
                disabled={!isEditable || isSaving}
                {...form.getInputProps("placesOfWork")}
              />
            </SimpleGrid>

            <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
              <NumberInput
                label={t("kp.booking_booklet_details.employees_count")}
                min={0}
                disabled={!isEditable || isSaving}
                {...form.getInputProps("employeesCount")}
              />
              <NumberInput
                label={t("kp.booking_booklet_details.employees_count_switzerland")}
                min={0}
                disabled={!isEditable || isSaving}
                {...form.getInputProps("employeesCountSwitzerland")}
              />
            </SimpleGrid>

            <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
              <NumberInput
                label={t("kp.booking_booklet_details.vacancies_worldwide")}
                min={0}
                disabled={!isEditable || isSaving}
                {...form.getInputProps("vacanciesWorldwide")}
              />
              <NumberInput
                label={t("kp.booking_booklet_details.vacancies_switzerland")}
                min={0}
                disabled={!isEditable || isSaving}
                {...form.getInputProps("vacanciesSwitzerland")}
              />
            </SimpleGrid>

            <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
              <NumberInput
                label={t("kp.booking_booklet_details.annual_revenue_chf_millions")}
                description={t(
                  "kp.booking_booklet_details.annual_revenue_chf_millions_hint",
                )}
                min={0}
                disabled={!isEditable || isSaving}
                {...form.getInputProps("annualRevenueChfMillions")}
              />
              <TextInput
                label={t("kp.booking_booklet_details.website")}
                placeholder="https://"
                disabled={!isEditable || isSaving}
                {...form.getInputProps("website")}
              />
            </SimpleGrid>

            <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
              <MultiSelect
                label={t("kp.booking_booklet_details.languages")}
                data={languageOptions}
                disabled={!isEditable || isSaving}
                {...form.getInputProps("languages")}
              />
              <MultiSelect
                label={t("kp.booking_booklet_details.industries")}
                data={industryOptions}
                searchable
                disabled={!isEditable || isSaving}
                {...form.getInputProps("industryIds")}
              />
            </SimpleGrid>

            <Checkbox.Group
              label={t("kp.booking_booklet_details.offers_title")}
              value={[
                form.values.offerInternship ? "internship" : "",
                form.values.offerPartTime ? "part_time" : "",
                form.values.offerThesis ? "thesis" : "",
              ].filter(Boolean)}
              onChange={(values) => {
                form.setFieldValue("offerInternship", values.includes("internship"));
                form.setFieldValue("offerPartTime", values.includes("part_time"));
                form.setFieldValue("offerThesis", values.includes("thesis"));
              }}
            >
              <Group mt="xs">
                <Checkbox
                  value="internship"
                  label={t("kp.booking_booklet_details.offer_internship")}
                  disabled={!isEditable || isSaving}
                />
                <Checkbox
                  value="part_time"
                  label={t("kp.booking_booklet_details.offer_part_time")}
                  disabled={!isEditable || isSaving}
                />
                <Checkbox
                  value="thesis"
                  label={t("kp.booking_booklet_details.offer_thesis")}
                  disabled={!isEditable || isSaving}
                />
              </Group>
            </Checkbox.Group>

            <Group justify="flex-end">
              <Button
                type="submit"
                leftSection={<IconDeviceFloppy size={16} />}
                loading={isSaving}
                disabled={!isEditable || isSaving || !form.isDirty()}
              >
                {t("kp.booking_booklet_details.save")}
              </Button>
            </Group>
          </Stack>
        </Paper>
      </form>

      <LogoSection
        bookingId={booking.id}
        logoUrl={details?.logo_url ?? null}
        isEditable={isEditable}
      />

      {event.advertisement_service_id ? (
        <AdvertisementSection
          booking={booking}
          advertisementServiceId={event.advertisement_service_id}
          isEditable={isEditable}
        />
      ) : null}
    </Stack>
  );
};

const LogoSection = ({
  bookingId,
  logoUrl,
  isEditable,
}: {
  bookingId: string;
  logoUrl: string | null;
  isEditable: boolean;
}) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [pendingFile, setPendingFile] = useState<File | null>(null);

  const invalidate = () =>
    queryClient.invalidateQueries({
      queryKey: getGetBookingCompanyDetailsQueryKey(bookingId),
    });

  const { mutateAsync: uploadLogo, isPending: isUploading } =
    useUploadBookingLogo();
  const { mutateAsync: deleteLogo, isPending: isDeleting } =
    useDeleteBookingLogo();

  const handleUpload = async () => {
    if (!pendingFile) return;
    try {
      await uploadLogo({ bookingId, data: { file: pendingFile } });
      setPendingFile(null);
      await invalidate();
      notifications.show({
        color: "green",
        message: t("kp.booking_booklet_details.logo_uploaded"),
      });
    } catch {
      notifications.show({
        color: "red",
        message: t("kp.booking_booklet_details.logo_upload_error"),
      });
    }
  };

  const handleDelete = async () => {
    if (!confirm(t("kp.booking_booklet_details.logo_delete_confirm"))) return;
    try {
      await deleteLogo({ bookingId });
      await invalidate();
      notifications.show({
        color: "green",
        message: t("kp.booking_booklet_details.logo_deleted"),
      });
    } catch {
      notifications.show({
        color: "red",
        message: t("kp.booking_booklet_details.logo_delete_error"),
      });
    }
  };

  return (
    <Paper withBorder p="lg" radius="md">
      <Stack gap="md">
        <div>
          <Title order={4}>{t("kp.booking_booklet_details.logo_title")}</Title>
          <Text c="dimmed" size="sm">
            {t("kp.booking_booklet_details.logo_description")}
          </Text>
        </div>

        <Group align="flex-end" gap="md" wrap="wrap">
          {logoUrl ? (
            <Group gap="xs" align="center">
              <img
                src={logoUrl}
                alt={t("kp.booking_booklet_details.logo_alt")}
                style={{ maxHeight: 64, maxWidth: 160 }}
              />
              <Badge color="green" variant="light">
                {t("kp.booking_booklet_details.logo_uploaded_badge")}
              </Badge>
            </Group>
          ) : (
            <Badge color="yellow" variant="light">
              {t("kp.booking_booklet_details.logo_missing_badge")}
            </Badge>
          )}

          <FileInput
            accept="image/*"
            disabled={!isEditable || isUploading || isDeleting}
            leftSection={<IconUpload size={16} />}
            placeholder={
              logoUrl
                ? t("kp.booking_booklet_details.logo_replace")
                : t("kp.booking_booklet_details.logo_upload")
            }
            size="sm"
            style={{ flex: "1 1 320px" }}
            value={pendingFile}
            onChange={setPendingFile}
          />
          <Button
            size="sm"
            onClick={handleUpload}
            loading={isUploading}
            disabled={!isEditable || !pendingFile}
          >
            {logoUrl
              ? t("kp.booking_booklet_details.logo_replace")
              : t("kp.booking_booklet_details.logo_upload")}
          </Button>
          {logoUrl && isEditable ? (
            <Button
              size="sm"
              variant="subtle"
              color="red"
              leftSection={<IconTrash size={14} />}
              loading={isDeleting}
              onClick={handleDelete}
            >
              {t("kp.booking_booklet_details.logo_delete")}
            </Button>
          ) : null}
        </Group>
      </Stack>
    </Paper>
  );
};

const AdvertisementSection = ({
  booking,
  advertisementServiceId,
  isEditable,
}: {
  booking: BookingResponse;
  advertisementServiceId: string;
  isEditable: boolean;
}) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [pendingFile, setPendingFile] = useState<File | null>(null);

  const bookingService = booking.services?.find(
    (entry) => entry.service_id === advertisementServiceId,
  );
  const requirement = bookingService?.service.requirements.find(
    (entry) =>
      entry.type === KpEventServiceRequirementType.pdf_single_page,
  );

  const { data: existingFile, isFetching: isCheckingFile } =
    useGetBookingRequirementFile(
      bookingService?.id ?? "",
      requirement?.id ?? "",
      {
        query: { enabled: Boolean(bookingService?.id && requirement?.id) },
      },
    );

  const invalidate = () =>
    bookingService && requirement
      ? queryClient.invalidateQueries({
          queryKey: getGetBookingRequirementFileQueryKey(
            bookingService.id,
            requirement.id,
          ),
        })
      : Promise.resolve();

  const { mutateAsync: uploadFile, isPending: isUploading } =
    useUploadBookingRequirementFile();
  const { mutateAsync: deleteFile, isPending: isDeleting } =
    useDeleteBookingRequirementFile();

  const [isDownloading, setIsDownloading] = useState(false);
  const handleDownload = async () => {
    if (!bookingService || !requirement) return;
    setIsDownloading(true);
    try {
      const response = await getBookingRequirementFileDownloadUrl(
        bookingService.id,
        requirement.id,
      );
      window.open(response.url, "_blank", "noopener,noreferrer");
    } finally {
      setIsDownloading(false);
    }
  };

  const handleUpload = async () => {
    if (!pendingFile || !bookingService || !requirement) return;
    try {
      await uploadFile({
        bookingServiceId: bookingService.id,
        requirementId: requirement.id,
        data: { file: pendingFile },
      });
      setPendingFile(null);
      await invalidate();
      notifications.show({
        color: "green",
        message: t("kp.booking_booklet_details.advertisement_uploaded"),
      });
    } catch {
      notifications.show({
        color: "red",
        message: t("kp.booking_booklet_details.advertisement_upload_error"),
      });
    }
  };

  const handleDelete = async () => {
    if (!bookingService || !requirement) return;
    if (!confirm(t("kp.booking_booklet_details.advertisement_delete_confirm")))
      return;
    try {
      await deleteFile({
        bookingServiceId: bookingService.id,
        requirementId: requirement.id,
      });
      await invalidate();
      notifications.show({
        color: "green",
        message: t("kp.booking_booklet_details.advertisement_deleted"),
      });
    } catch {
      notifications.show({
        color: "red",
        message: t("kp.booking_booklet_details.advertisement_delete_error"),
      });
    }
  };

  return (
    <Paper withBorder p="lg" radius="md">
      <Stack gap="md">
        <div>
          <Title order={4}>
            {t("kp.booking_booklet_details.advertisement_title")}
          </Title>
          <Text c="dimmed" size="sm">
            {t("kp.booking_booklet_details.advertisement_description")}
          </Text>
        </div>

        {!bookingService || !requirement ? (
          <Alert color="blue">
            {t("kp.booking_booklet_details.advertisement_not_booked")}
          </Alert>
        ) : (
          <>
            <Group gap="xs" align="center">
              <Text size="sm">
                {isCheckingFile
                  ? t("kp.booking_manage.checking_file")
                  : existingFile
                    ? existingFile.stored_file.original_filename
                    : t("kp.booking_booklet_details.advertisement_no_file")}
              </Text>
              {existingFile ? (
                <Badge color="green" variant="light">
                  {t("kp.booking_booklet_details.advertisement_uploaded_badge")}
                </Badge>
              ) : (
                <Badge color="yellow" variant="light">
                  {t("kp.booking_booklet_details.advertisement_missing_badge")}
                </Badge>
              )}
            </Group>

            <Group align="flex-end" gap="xs" wrap="wrap">
              <FileInput
                accept="application/pdf"
                disabled={!isEditable || isUploading || isDeleting}
                leftSection={<IconUpload size={16} />}
                placeholder={
                  existingFile
                    ? t("kp.booking_booklet_details.advertisement_replace")
                    : t("kp.booking_booklet_details.advertisement_upload")
                }
                size="sm"
                style={{ flex: "1 1 320px" }}
                value={pendingFile}
                onChange={setPendingFile}
              />
              <Button
                size="sm"
                onClick={handleUpload}
                loading={isUploading}
                disabled={!isEditable || !pendingFile}
              >
                {existingFile
                  ? t("kp.booking_booklet_details.advertisement_replace")
                  : t("kp.booking_booklet_details.advertisement_upload")}
              </Button>
              {existingFile ? (
                <Button
                  size="sm"
                  variant="subtle"
                  leftSection={<IconDownload size={14} />}
                  loading={isDownloading}
                  onClick={handleDownload}
                >
                  {t("kp.booking_booklet_details.advertisement_download")}
                </Button>
              ) : null}
              {existingFile && isEditable ? (
                <Button
                  size="sm"
                  variant="subtle"
                  color="red"
                  leftSection={<IconTrash size={14} />}
                  loading={isDeleting}
                  onClick={handleDelete}
                >
                  {t("kp.booking_booklet_details.advertisement_delete")}
                </Button>
              ) : null}
            </Group>
          </>
        )}
      </Stack>
    </Paper>
  );
};

export default KpBookingBookletDetails;
