import {
  Alert,
  Badge,
  Button,
  Card,
  Center,
  FileInput,
  Group,
  Loader,
  NumberInput,
  Paper,
  SimpleGrid,
  Stack,
  Text,
  Textarea,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  IconAlertCircle,
  IconDeviceFloppy,
  IconDownload,
  IconPlus,
  IconTrash,
  IconUpload,
} from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router";
import { useListAvailableServices } from "../api/kp-services";
import BackButton from "../components/BackButton";
import {
  KpBookingStatus,
  KpEventServiceRequirementType,
  type BookingServiceResponse,
  type ServiceRequirementResponse,
  type ServiceResponse,
} from "../orval/generated/fastAPI.schemas";
import {
  getBookingRequirementFileDownloadUrl,
  getGetBookingRequirementFileQueryKey,
  getGetMyBookingQueryKey,
  useAddBookingServices,
  useDeleteBookingRequirementFile,
  useGetBookingRequirementFile,
  useGetKpById,
  useGetMyBooking,
  useUpsertBookingRequirementText,
  useUploadBookingRequirementFile,
} from "../orval/generated/kp/kp";
import { formatPrice } from "../utils/price-utils";

type RequirementDraft = {
  text?: string;
  file?: File | null;
};

const requirementTypeLabel = (
  type: KpEventServiceRequirementType,
  t: (key: string) => string,
) => {
  if (type === KpEventServiceRequirementType.text) {
    return t("kp.booking.requirement_type_text");
  }
  if (type === KpEventServiceRequirementType.image) {
    return t("kp.booking.requirement_type_image");
  }
  if (type === KpEventServiceRequirementType.pdf) {
    return t("kp.booking.requirement_type_pdf");
  }
  if (type === KpEventServiceRequirementType.video) {
    return t("kp.booking.requirement_type_video");
  }
  return t("kp.booking.requirement_type_file");
};

const acceptForRequirement = (type: KpEventServiceRequirementType) => {
  if (type === KpEventServiceRequirementType.image) return "image/*";
  if (type === KpEventServiceRequirementType.pdf) return "application/pdf";
  if (type === KpEventServiceRequirementType.video) return "video/*";
  return undefined;
};

const RequirementEditor = ({
  bookingServiceId,
  editable,
  requirement,
}: {
  bookingServiceId: string;
  editable: boolean;
  requirement: ServiceRequirementResponse;
}) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState<RequirementDraft>({});
  const isText = requirement.type === KpEventServiceRequirementType.text;
  const { data: requirementFile, isFetching } = useGetBookingRequirementFile(
    bookingServiceId,
    requirement.id,
    {
      query: {
        enabled: !isText,
        retry: false,
      },
    },
  );
  const { mutateAsync: uploadFile, isPending: isUploading } =
    useUploadBookingRequirementFile();
  const { mutateAsync: saveText, isPending: isSavingText } =
    useUpsertBookingRequirementText();
  const { mutateAsync: deleteFile, isPending: isDeleting } =
    useDeleteBookingRequirementFile();

  const invalidateRequirementFile = () =>
    queryClient.invalidateQueries({
      queryKey: getGetBookingRequirementFileQueryKey(
        bookingServiceId,
        requirement.id,
      ),
    });

  const handleDownload = async () => {
    const response = await getBookingRequirementFileDownloadUrl(
      bookingServiceId,
      requirement.id,
    );
    window.location.assign(response.url);
  };

  const handleSave = async () => {
    if (!editable) return;
    if (isText) {
      const text = draft.text?.trim();
      if (!text) return;
      await saveText({
        bookingServiceId,
        requirementId: requirement.id,
        data: { text_value: text },
      });
      notifications.show({
        color: "green",
        message: t("kp.booking_manage.requirement_saved"),
      });
      return;
    }

    if (!draft.file) return;
    await uploadFile({
      bookingServiceId,
      requirementId: requirement.id,
      data: { file: draft.file },
    });
    setDraft((current) => ({ ...current, file: null }));
    await invalidateRequirementFile();
    notifications.show({
      color: "green",
      message: t("kp.booking_manage.requirement_saved"),
    });
  };

  const handleDelete = async () => {
    if (!editable || !requirementFile) return;
    await deleteFile({
      bookingServiceId,
      requirementId: requirement.id,
    });
    await invalidateRequirementFile();
    notifications.show({
      color: "green",
      message: t("kp.booking_manage.requirement_deleted"),
    });
  };

  return (
    <Stack
      gap="xs"
      py="sm"
      style={{ borderTop: "1px solid var(--mantine-color-default-border)" }}
    >
      <Group justify="space-between" align="flex-start" gap="md">
        <div style={{ minWidth: 220, flex: "0 1 34%" }}>
          <Group gap="xs">
            <Text size="sm" fw={600}>
              {requirement.name}
            </Text>
            <Badge variant="light" size="xs">
              {requirementTypeLabel(requirement.type, t)}
            </Badge>
          </Group>
          <Text c="dimmed" size="xs">
            {requirement.description}
          </Text>
          {!isText ? (
            <Text c="dimmed" size="xs" mt={4}>
              {isFetching
                ? t("kp.booking_manage.checking_file")
                : requirementFile
                  ? requirementFile.stored_file.original_filename
                  : t("kp.booking_manage.no_file")}
            </Text>
          ) : null}
        </div>

        <Group align="flex-end" gap="xs" style={{ flex: "1 1 420px" }}>
          {isText ? (
            <Textarea
              autosize
              minRows={1}
              disabled={!editable}
              placeholder={t("kp.booking_manage.text_placeholder")}
              size="sm"
              style={{ flex: "1 1 300px" }}
              value={draft.text ?? ""}
              onChange={(event) =>
                setDraft((current) => ({
                  ...current,
                  text: event.currentTarget.value,
                }))
              }
            />
          ) : (
            <FileInput
              disabled={!editable}
              accept={acceptForRequirement(requirement.type)}
              leftSection={<IconUpload size={16} />}
              placeholder={
                requirementFile
                  ? t("kp.booking_manage.replace_file")
                  : t("kp.booking_manage.upload_file")
              }
              size="sm"
              style={{ flex: "1 1 260px" }}
              value={draft.file ?? null}
              onChange={(file) =>
                setDraft((current) => ({
                  ...current,
                  file,
                }))
              }
            />
          )}

          {!isText && requirementFile ? (
            <Button
              size="xs"
              variant="subtle"
              leftSection={<IconDownload size={14} />}
              onClick={handleDownload}
            >
              {t("kp.booking_manage.download_file")}
            </Button>
          ) : null}
          {!isText && requirementFile && editable ? (
            <Button
              color="red"
              size="xs"
              variant="subtle"
              leftSection={<IconTrash size={14} />}
              loading={isDeleting}
              onClick={handleDelete}
            >
              {t("kp.booking_manage.delete_file")}
            </Button>
          ) : null}
          <Button
            size="xs"
            leftSection={<IconDeviceFloppy size={14} />}
            disabled={
              !editable ||
              (isText ? !draft.text?.trim() : !draft.file) ||
              isUploading ||
              isSavingText
            }
            loading={isUploading || isSavingText}
            onClick={handleSave}
          >
            {t("kp.booking_manage.save_requirement")}
          </Button>
        </Group>
      </Group>
    </Stack>
  );
};

const BookedServiceCard = ({
  bookingService,
  editable,
}: {
  bookingService: BookingServiceResponse;
  editable: boolean;
}) => (
  <Card withBorder radius="md" p="lg">
    <Stack gap="md">
      <Group justify="space-between" align="flex-start">
        <div>
          <Text fw={600}>{bookingService.service.name}</Text>
          {bookingService.service.description ? (
            <Text c="dimmed" size="sm">
              {bookingService.service.description}
            </Text>
          ) : null}
        </div>
        <Badge variant="light">x{bookingService.quantity}</Badge>
      </Group>
      {bookingService.service.requirements.length ? (
        <Stack gap={0}>
          {bookingService.service.requirements
            .slice()
            .sort((a, b) => a.order - b.order)
            .map((requirement) => (
              <RequirementEditor
                bookingServiceId={bookingService.id}
                editable={editable}
                key={requirement.id}
                requirement={requirement}
              />
            ))}
        </Stack>
      ) : null}
    </Stack>
  </Card>
);

const AddServicesForm = ({
  bookingId,
  bookingServices,
  editable,
  eventId,
  onAdded,
}: {
  bookingId: string;
  bookingServices: BookingServiceResponse[];
  editable: boolean;
  eventId: string;
  onAdded: () => void;
}) => {
  const { t } = useTranslation();
  const [quantities, setQuantities] = useState<Record<string, number>>({});
  const { data: availableServices, isLoading } = useListAvailableServices(eventId);
  const { mutateAsync: addServices, isPending } = useAddBookingServices();
  const bookingServiceByServiceId = useMemo(
    () => new Map(bookingServices.map((item) => [item.service_id, item])),
    [bookingServices],
  );
  const services = availableServices ?? [];
  const selectedServices = services
    .map((service) => ({
      service,
      quantity: quantities[service.id] ?? 0,
    }))
    .filter((item) => item.quantity > 0);

  const handleSubmit = async (bookingId: string) => {
    const payload = selectedServices.map((item) => ({
      service_id: item.service.id,
      quantity: item.quantity,
    }));
    if (!payload.length) return;
    await addServices({
      bookingId,
      data: { services: payload },
    });
    setQuantities({});
    onAdded();
    notifications.show({
      color: "green",
      message: t("kp.booking_manage.services_added"),
    });
  };

  return (
    <Card withBorder radius="md" p="lg">
      <Stack gap="md">
        <div>
          <Title order={4}>{t("kp.booking_manage.add_services_title")}</Title>
          <Text c="dimmed" size="sm">
            {t("kp.booking_manage.add_services_description")}
          </Text>
        </div>

        {isLoading ? (
          <Center py="md">
            <Loader size="sm" />
          </Center>
        ) : services.length ? (
          <SimpleGrid cols={{ base: 1, md: 2 }} spacing="sm">
            {services.map((service: ServiceResponse) => {
              const bookedQuantity =
                bookingServiceByServiceId.get(service.id)?.quantity ?? 0;
              const remaining = Math.max(
                service.max_quantity_per_booking - bookedQuantity,
                0,
              );
              return (
                <Paper withBorder radius="sm" p="md" key={service.id}>
                  <Stack gap="xs">
                    <Group justify="space-between" align="flex-start">
                      <div>
                        <Text fw={600}>{service.name}</Text>
                        {service.description ? (
                          <Text c="dimmed" size="sm">
                            {service.description}
                          </Text>
                        ) : null}
                      </div>
                      <Text fw={600} size="sm">
                        CHF {formatPrice(service.price)}
                      </Text>
                    </Group>
                    <Text c="dimmed" size="xs">
                      {t("kp.booking_manage.current_quantity", {
                        quantity: bookedQuantity,
                      })}
                    </Text>
                    <NumberInput
                      disabled={!editable || remaining <= 0}
                      label={t("kp.booking.service_quantity")}
                      min={0}
                      max={remaining}
                      value={quantities[service.id] ?? 0}
                      onChange={(value) =>
                        setQuantities((current) => ({
                          ...current,
                          [service.id]:
                            typeof value === "number"
                              ? value
                              : Number(value) || 0,
                        }))
                      }
                    />
                  </Stack>
                </Paper>
              );
            })}
          </SimpleGrid>
        ) : (
          <Text c="dimmed" size="sm">
            {t("kp.booking.services_none_available")}
          </Text>
        )}

        <Group justify="flex-end">
          <Button
            leftSection={<IconPlus size={16} />}
            disabled={!editable || selectedServices.length === 0}
            loading={isPending}
            onClick={() => {
              void handleSubmit(bookingId);
            }}
          >
            {t("kp.booking_manage.add_services_submit")}
          </Button>
        </Group>
      </Stack>
    </Card>
  );
};

const KpBookingManage = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { id = "", bookingId = "" } = useParams<{
    id: string;
    bookingId: string;
  }>();
  const eventId = id.trim();
  const normalizedBookingId = bookingId.trim();
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
    isFetching: isFetchingBooking,
    isError: isBookingError,
  } = useGetMyBooking(eventId, {
    query: { enabled: Boolean(eventId) },
  });
  const bookingServices = booking?.services ?? [];
  const isEditable =
    booking?.status !== KpBookingStatus.CONFIRMED &&
    booking?.status !== KpBookingStatus.CANCELLED;

  const refreshBooking = () => {
    void queryClient.invalidateQueries({
      queryKey: getGetMyBookingQueryKey(eventId),
    });
  };

  if (isLoadingEvent || isLoadingBooking || isFetchingBooking) {
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

  return (
    <Stack gap="md">
      <BackButton to={`/kp/${eventId}/booking/${booking.id}/manage`} />
      <Group justify="space-between" align="flex-start">
        <div>
          <Title order={2}>{t("kp.booking_manage.services_page_title")}</Title>
          <Text c="dimmed" size="sm">
            {t("kp.booking_manage.services_page_subtitle", {
              eventName: event.name,
              bookingNumber: booking.booking_number,
            })}
          </Text>
        </div>
        <Button
          variant="light"
          onClick={() => navigate(`/kp/${eventId}/booking/${booking.id}`)}
        >
          {t("kp.booking_manage.view_summary")}
        </Button>
      </Group>

      {!isEditable ? (
        <Alert icon={<IconAlertCircle />} color="yellow">
          {t("kp.booking_manage.readonly_notice")}
        </Alert>
      ) : null}

      <AddServicesForm
        bookingId={booking.id}
        bookingServices={bookingServices}
        editable={isEditable}
        eventId={eventId}
        onAdded={refreshBooking}
      />

      <Stack gap="md">
        <div>
          <Title order={4}>{t("kp.booking_manage.requirements_title")}</Title>
          <Text c="dimmed" size="sm">
            {t("kp.booking_manage.requirements_description")}
          </Text>
        </div>
        {bookingServices.length ? (
          <Stack gap="sm">
            {bookingServices.map((bookingService) => (
              <BookedServiceCard
                bookingService={bookingService}
                editable={isEditable}
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
    </Stack>
  );
};

export default KpBookingManage;
