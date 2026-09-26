import {
  ActionIcon,
  Alert,
  Badge,
  Button,
  Card,
  Center,
  FileInput,
  Group,
  Loader,
  Modal,
  NumberInput,
  Paper,
  SimpleGrid,
  Stack,
  Switch,
  Tabs,
  Text,
  Textarea,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  IconAlertCircle,
  IconArrowBackUp,
  IconCheck,
  IconDeviceFloppy,
  IconDownload,
  IconPlus,
  IconProgressCheck,
  IconRefresh,
  IconTrash,
  IconUpload,
} from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Navigate, useNavigate, useParams } from "react-router";
import BackButton from "../components/BackButton";
import { KpBookingCompletion } from "../components/KpBookingCompletion";
import {
  KpEventServiceRequirementType,
  KpServiceCategory,
  type BookingResponse,
  type BookingServiceResponse,
  type ServiceRequirementResponse,
  type ServiceResponse,
} from "../orval/generated/fastAPI.schemas";
import {
  getBookingRequirementFileDownloadUrl,
  getGetBookingRequirementFileQueryKey,
  getGetBookingRequirementTextQueryKey,
  getGetMyBookingQueryKey,
  useAddBookingServices,
  useDeleteBookingRequirementFile,
  useGetBookingRequirementFile,
  useGetBookingRequirementText,
  useGetKpById,
  useGetMyBooking,
  useListAvailableServices,
  useUpsertBookingRequirementText,
  useUploadBookingRequirementFile,
} from "../orval/generated/kp/kp";
import {
  maxServiceQuantity,
  servicesOfCategory,
} from "../utils/kp-service-quantity";
import { isInactiveBooking } from "../utils/my-booking";
import { bookingRequirementElementId } from "../utils/navigation";
import { useScrollToHash } from "../utils/use-scroll-to-hash";
import { formatPrice } from "../utils/price-utils";
import { priceBreakdown } from "../utils/pricing";
import {
  acceptForRequirement,
  allowedFormatsLabel,
} from "../utils/upload-formats";

type RequirementDraft = {
  text?: string;
  file?: File | null;
};

type PendingRequirementChange =
  | {
      kind: "text";
      bookingServiceId: string;
      requirementId: string;
      serviceName: string;
      requirementName: string;
      text: string;
    }
  | {
      kind: "file";
      bookingServiceId: string;
      requirementId: string;
      serviceName: string;
      requirementName: string;
      file: File;
    }
  | {
      kind: "delete_file";
      bookingServiceId: string;
      requirementId: string;
      serviceName: string;
      requirementName: string;
    };

type RequirementCompletion = Record<string, boolean>;

const requirementChangeKey = (
  bookingServiceId: string,
  requirementId: string,
) => `${bookingServiceId}:${requirementId}`;

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

const requirementChangeLabel = (
  change: PendingRequirementChange,
  t: (key: string) => string,
) => {
  if (change.kind === "text") return t("kp.booking_manage.change_text");
  if (change.kind === "file") return t("kp.booking_manage.change_file");
  return t("kp.booking_manage.change_delete_file");
};

const RequirementEditor = ({
  bookingServiceId,
  editable,
  onChange,
  onCompletionChange,
  pendingChange,
  requirement,
  serviceName,
}: {
  bookingServiceId: string;
  editable: boolean;
  onChange: (
    bookingServiceId: string,
    requirementId: string,
    change: PendingRequirementChange | null,
  ) => void;
  onCompletionChange: (
    bookingServiceId: string,
    requirementId: string,
    isComplete: boolean,
  ) => void;
  pendingChange?: PendingRequirementChange;
  requirement: ServiceRequirementResponse;
  serviceName: string;
}) => {
  const { t } = useTranslation();
  const [draft, setDraft] = useState<RequirementDraft>({});
  const isText = requirement.type === KpEventServiceRequirementType.text;
  const {
    data: requirementFile,
    isFetching,
    isError: isFileError,
    refetch: refetchFile,
  } = useGetBookingRequirementFile(bookingServiceId, requirement.id, {
    query: {
      enabled: !isText,
      retry: false,
    },
  });
  const { data: requirementText, isFetched: isTextFetched } =
    useGetBookingRequirementText(bookingServiceId, requirement.id, {
      query: {
        enabled: isText,
        retry: false,
      },
    });
  const requirementTextValue = requirementText?.text_value ?? "";
  useEffect(() => {
    if (!isText || !isTextFetched || draft.text !== undefined) return;
    setDraft((current) => ({
      ...current,
      text:
        pendingChange?.kind === "text"
          ? pendingChange.text
          : requirementTextValue,
    }));
  }, [draft.text, isText, isTextFetched, pendingChange, requirementTextValue]);
  useEffect(() => {
    if (isText) return;
    const pendingFile =
      pendingChange?.kind === "file" ? pendingChange.file : null;
    if ((draft.file ?? null) === pendingFile) return;
    setDraft((current) => ({ ...current, file: pendingFile }));
  }, [draft.file, isText, pendingChange]);
  useEffect(() => {
    const isComplete = isText
      ? pendingChange?.kind === "text"
        ? Boolean(pendingChange.text.trim())
        : Boolean(requirementTextValue.trim())
      : pendingChange?.kind === "delete_file"
        ? false
        : pendingChange?.kind === "file" || Boolean(requirementFile);
    onCompletionChange(bookingServiceId, requirement.id, isComplete);
  }, [
    bookingServiceId,
    isText,
    onCompletionChange,
    pendingChange,
    requirement.id,
    requirementFile,
    requirementTextValue,
  ]);

  const handleDownload = async () => {
    const response = await getBookingRequirementFileDownloadUrl(
      bookingServiceId,
      requirement.id,
    );
    window.location.assign(response.url);
  };

  return (
    <Stack
      gap="xs"
      id={bookingRequirementElementId(requirement.id)}
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
                : isFileError
                  ? t("kp.booking_manage.file_load_error")
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
              maxRows={14}
              minRows={6}
              disabled={!editable}
              placeholder={t("kp.booking_manage.text_placeholder")}
              size="sm"
              style={{ flex: "1 1 520px" }}
              value={draft.text ?? ""}
              onChange={(event) => {
                const text = event.currentTarget.value;
                const trimmed = text.trim();
                setDraft((current) => ({
                  ...current,
                  text,
                }));
                onChange(
                  bookingServiceId,
                  requirement.id,
                  trimmed && trimmed !== requirementTextValue
                    ? {
                        kind: "text",
                        bookingServiceId,
                        requirementId: requirement.id,
                        serviceName,
                        requirementName: requirement.name,
                        text: trimmed,
                      }
                    : null,
                );
              }}
            />
          ) : isFileError ? (
            <Button
              leftSection={<IconRefresh size={16} />}
              onClick={() => {
                void refetchFile();
              }}
              size="sm"
              variant="light"
            >
              {t("kp.booking_manage.retry_file_load")}
            </Button>
          ) : (
            <FileInput
              disabled={!editable}
              accept={acceptForRequirement(requirement.type)}
              description={allowedFormatsLabel(requirement.type, t)}
              leftSection={<IconUpload size={16} />}
              placeholder={
                requirementFile
                  ? t("kp.booking_manage.replace_file")
                  : t("kp.booking_manage.upload_file")
              }
              size="sm"
              style={{ flex: "1 1 260px" }}
              value={draft.file ?? null}
              onChange={(file) => {
                setDraft((current) => ({
                  ...current,
                  file,
                }));
                onChange(
                  bookingServiceId,
                  requirement.id,
                  file
                    ? {
                        kind: "file",
                        bookingServiceId,
                        requirementId: requirement.id,
                        serviceName,
                        requirementName: requirement.name,
                        file,
                      }
                    : null,
                );
              }}
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
              onClick={() => {
                setDraft((current) => ({ ...current, file: null }));
                onChange(
                  bookingServiceId,
                  requirement.id,
                  pendingChange?.kind === "delete_file"
                    ? null
                    : {
                        kind: "delete_file",
                        bookingServiceId,
                        requirementId: requirement.id,
                        serviceName,
                        requirementName: requirement.name,
                      },
                );
              }}
            >
              {pendingChange?.kind === "delete_file"
                ? t("kp.booking_manage.undo_delete_file")
                : t("kp.booking_manage.delete_file")}
            </Button>
          ) : null}
          {pendingChange ? (
            <Badge variant="light">
              {t("kp.booking_manage.pending_change")}
            </Badge>
          ) : null}
        </Group>
      </Group>
    </Stack>
  );
};

const BookedServiceCard = ({
  bookingService,
  completion,
  editable,
  onRequirementCompletionChange,
  onRequirementChange,
  pendingChanges,
}: {
  bookingService: BookingServiceResponse;
  completion: RequirementCompletion;
  editable: boolean;
  onRequirementCompletionChange: (
    bookingServiceId: string,
    requirementId: string,
    isComplete: boolean,
  ) => void;
  onRequirementChange: (
    bookingServiceId: string,
    requirementId: string,
    change: PendingRequirementChange | null,
  ) => void;
  pendingChanges: Record<string, PendingRequirementChange>;
}) => {
  const { t } = useTranslation();
  const requirements = bookingService.service.requirements
    .slice()
    .sort((a, b) => a.order - b.order);
  const completedRequirements = requirements.filter(
    (requirement) =>
      completion[requirementChangeKey(bookingService.id, requirement.id)],
  ).length;
  const allRequirementsComplete =
    requirements.length === 0 || completedRequirements === requirements.length;

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
          <Badge
            color={allRequirementsComplete ? "green" : "yellow"}
            leftSection={
              allRequirementsComplete ? (
                <IconCheck size={12} />
              ) : (
                <IconProgressCheck size={12} />
              )
            }
            variant="light"
          >
            {requirements.length
              ? t("kp.booking_manage.requirements_completed_count", {
                  completed: completedRequirements,
                  total: requirements.length,
                })
              : t("kp.booking_manage.no_requirements")}
          </Badge>
        </Group>
        {requirements.length ? (
          <Stack gap={0}>
            {requirements.map((requirement) => (
              <RequirementEditor
                bookingServiceId={bookingService.id}
                editable={editable}
                key={requirement.id}
                onChange={onRequirementChange}
                onCompletionChange={onRequirementCompletionChange}
                pendingChange={
                  pendingChanges[
                    requirementChangeKey(bookingService.id, requirement.id)
                  ]
                }
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

const AddServiceCard = ({
  bookedQuantity,
  editable,
  includedQuantity,
  onQuantityChange,
  quantity,
  service,
}: {
  bookedQuantity: number;
  editable: boolean;
  includedQuantity: number;
  onQuantityChange: (quantity: number) => void;
  quantity: number;
  service: ServiceResponse;
}) => {
  const { t } = useTranslation();
  const maxQuantity = maxServiceQuantity(service, bookedQuantity);
  const addedQuantity = Math.max(quantity - bookedQuantity, 0);

  return (
    <Paper withBorder radius="sm" p="md">
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
          <Stack gap={4} align="flex-end">
            <Text fw={600} size="sm">
              CHF {formatPrice(service.price)}
            </Text>
            {includedQuantity > 0 ? (
              <Badge color="green" variant="light">
                {t("kp.booking.service_included_note", {
                  included: includedQuantity,
                })}
              </Badge>
            ) : null}
          </Stack>
        </Group>
        {service.max_quantity_per_booking === 1 ? (
          <Switch
            checked={quantity > 0}
            disabled={!editable || maxQuantity <= bookedQuantity}
            label={t("kp.booking.service_book_toggle")}
            onChange={(event) =>
              onQuantityChange(event.currentTarget.checked ? 1 : 0)
            }
          />
        ) : (
          <NumberInput
            allowDecimal={false}
            allowNegative={false}
            clampBehavior="strict"
            disabled={!editable || maxQuantity <= bookedQuantity}
            label={
              service.unit_label
                ? t("kp.booking.service_quantity_with_unit", {
                    unit: service.unit_label,
                  })
                : t("kp.booking.service_quantity")
            }
            min={bookedQuantity}
            max={maxQuantity}
            step={1}
            value={quantity}
            onChange={(value) =>
              onQuantityChange(
                typeof value === "number" ? value : Number(value) || 0,
              )
            }
          />
        )}
        {service.remaining_total_quantity != null ? (
          <Text c="dimmed" size="xs">
            {t("kp.booking.service_remaining_total", {
              remaining: service.remaining_total_quantity,
            })}
          </Text>
        ) : null}
        {addedQuantity > 0 ? (
          <Group justify="space-between" wrap="nowrap">
            <Text size="sm" c="dimmed">
              {t("kp.booking.service_line_total")}
            </Text>
            <Text fw={600} size="sm">
              CHF {formatPrice(service.price * addedQuantity)}
            </Text>
          </Group>
        ) : null}
      </Stack>
    </Paper>
  );
};

const AddServicesForm = ({
  bookingId,
  bookingServices,
  editable,
  eventId,
  onAdded,
  vatRatePercent,
}: {
  bookingId: string;
  bookingServices: BookingServiceResponse[];
  editable: boolean;
  eventId: string;
  onAdded: (booking: BookingResponse, serviceIds: string[]) => void;
  vatRatePercent: number;
}) => {
  const { t } = useTranslation();
  const [quantities, setQuantities] = useState<Record<string, number>>({});
  const [confirmOpen, setConfirmOpen] = useState(false);
  const { data: availableServices, isLoading } =
    useListAvailableServices(eventId);
  const { mutateAsync: addServices, isPending } = useAddBookingServices();
  const bookingServiceByServiceId = useMemo(
    () => new Map(bookingServices.map((item) => [item.service_id, item])),
    [bookingServices],
  );
  const services = useMemo(() => availableServices ?? [], [availableServices]);
  const selectedServices = services
    .map((service) => {
      const bookedQuantity =
        bookingServiceByServiceId.get(service.id)?.quantity ?? 0;
      const selectedQuantity = quantities[service.id] ?? bookedQuantity;
      return {
        service,
        bookedQuantity,
        quantity: selectedQuantity - bookedQuantity,
      };
    })
    .filter((item) => item.quantity > 0);
  const selectedTotal = selectedServices.reduce(
    (sum, item) => sum + item.service.price * item.quantity,
    0,
  );
  const selectedPrice = priceBreakdown(selectedTotal, vatRatePercent);

  const handleSubmit = async (bookingId: string) => {
    const payload = selectedServices.map((item) => ({
      service_id: item.service.id,
      quantity: item.quantity,
    }));
    if (!payload.length) return;
    const updated = await addServices({
      bookingId,
      data: { services: payload },
    });
    setQuantities({});
    setConfirmOpen(false);
    onAdded(
      updated,
      payload.map((item) => item.service_id),
    );
    notifications.show({
      color: "green",
      message: t("kp.booking_manage.services_added"),
    });
  };

  const renderCategory = (category: KpServiceCategory, emptyLabel: string) => {
    const categoryServices = servicesOfCategory(services, category);
    if (isLoading) {
      return (
        <Center py="md">
          <Loader size="sm" />
        </Center>
      );
    }
    if (categoryServices.length === 0) {
      return (
        <Text c="dimmed" size="sm">
          {emptyLabel}
        </Text>
      );
    }
    return (
      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="sm">
        {categoryServices.map((service) => {
          const bookingService = bookingServiceByServiceId.get(service.id);
          const bookedQuantity = bookingService?.quantity ?? 0;
          return (
            <AddServiceCard
              bookedQuantity={bookedQuantity}
              editable={editable}
              includedQuantity={bookingService?.included_quantity ?? 0}
              key={service.id}
              onQuantityChange={(quantity) =>
                setQuantities((current) => ({
                  ...current,
                  [service.id]: quantity,
                }))
              }
              quantity={quantities[service.id] ?? bookedQuantity}
              service={service}
            />
          );
        })}
      </SimpleGrid>
    );
  };

  return (
    <Card withBorder radius="md" p="lg">
      <Modal
        centered
        opened={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        title={t("kp.booking_manage.confirm_add_services_title")}
      >
        <Stack gap="md">
          <Text size="sm">
            {t("kp.booking_manage.confirm_add_services_body")}
          </Text>
          <Stack gap="xs">
            {selectedServices.map((item) => (
              <Group justify="space-between" key={item.service.id}>
                <Text size="sm">
                  {item.service.name} × {item.quantity}
                </Text>
                <Text size="sm" fw={600}>
                  CHF {formatPrice(item.service.price * item.quantity)}
                </Text>
              </Group>
            ))}
          </Stack>
          <Group justify="space-between">
            <Text size="sm">{t("kp.booking.summary_net")}</Text>
            <Text size="sm">CHF {formatPrice(selectedTotal)}</Text>
          </Group>
          <Group justify="space-between">
            <Text size="sm">
              {t("kp.booking.summary_vat_rate", { rate: vatRatePercent })}
            </Text>
            <Text size="sm">CHF {formatPrice(selectedPrice.vat)}</Text>
          </Group>
          <Group justify="space-between">
            <Text fw={600}>{t("kp.booking.summary_gross")}</Text>
            <Text fw={700}>CHF {formatPrice(selectedPrice.gross)}</Text>
          </Group>
          <Group justify="flex-end">
            <Button variant="subtle" onClick={() => setConfirmOpen(false)}>
              {t("common.cancel")}
            </Button>
            <Button
              leftSection={<IconPlus size={16} />}
              loading={isPending}
              onClick={() => {
                void handleSubmit(bookingId);
              }}
            >
              {t("kp.booking_manage.confirm_add_services_submit")}
            </Button>
          </Group>
        </Stack>
      </Modal>
      <Stack gap="md">
        <div>
          <Title order={4}>{t("kp.booking_manage.add_services_title")}</Title>
          <Text c="dimmed" size="sm">
            {t("kp.booking_manage.add_services_description")}
          </Text>
        </div>

        <Tabs defaultValue="services" keepMounted={false}>
          <Tabs.List mb="md">
            <Tabs.Tab value="services">
              {t("kp.booking_manage.add_services_tab_services")}
            </Tabs.Tab>
            <Tabs.Tab value="booth_elements">
              {t("kp.booking_manage.add_services_tab_booth_elements")}
            </Tabs.Tab>
          </Tabs.List>
          <Tabs.Panel value="services">
            {renderCategory(
              KpServiceCategory.SERVICE,
              t("kp.booking.services_none_available"),
            )}
          </Tabs.Panel>
          <Tabs.Panel value="booth_elements">
            {renderCategory(
              KpServiceCategory.BOOTH_ELEMENT,
              t("kp.booking.booth_none_available"),
            )}
          </Tabs.Panel>
        </Tabs>

        <Group justify="flex-end">
          <Button
            leftSection={<IconPlus size={16} />}
            disabled={!editable || selectedServices.length === 0}
            loading={isPending}
            onClick={() => {
              setConfirmOpen(true);
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
  useScrollToHash();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [confirmRequirementsOpen, setConfirmRequirementsOpen] = useState(false);
  const [pendingNavigationTo, setPendingNavigationTo] = useState<string | null>(
    null,
  );
  const [pendingRequirementChanges, setPendingRequirementChanges] = useState<
    Record<string, PendingRequirementChange>
  >({});
  const [requirementCompletion, setRequirementCompletion] =
    useState<RequirementCompletion>({});
  const [promptedServices, setPromptedServices] = useState<
    BookingServiceResponse[]
  >([]);
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
    isError: isBookingError,
  } = useGetMyBooking(eventId, {
    query: { enabled: Boolean(eventId) },
  });
  const bookingServices = booking?.services ?? [];
  const isEditable = booking != null && !isInactiveBooking(booking);
  const pendingRequirementChangeList = Object.values(pendingRequirementChanges);
  const hasPendingRequirementChanges = pendingRequirementChangeList.length > 0;
  const allRequirementKeys = bookingServices.flatMap((bookingService) =>
    bookingService.service.requirements.map((requirement) =>
      requirementChangeKey(bookingService.id, requirement.id),
    ),
  );
  const completedRequirementCount = allRequirementKeys.filter(
    (key) => requirementCompletion[key],
  ).length;
  const totalRequirementCount = allRequirementKeys.length;
  const allRequirementsComplete =
    totalRequirementCount === 0 ||
    completedRequirementCount === totalRequirementCount;
  const {
    mutateAsync: uploadRequirementFile,
    isPending: isUploadingRequirementFile,
  } = useUploadBookingRequirementFile();
  const {
    mutateAsync: saveRequirementText,
    isPending: isSavingRequirementText,
  } = useUpsertBookingRequirementText();
  const {
    mutateAsync: deleteRequirementFile,
    isPending: isDeletingRequirementFile,
  } = useDeleteBookingRequirementFile();
  const isSavingRequirements =
    isUploadingRequirementFile ||
    isSavingRequirementText ||
    isDeletingRequirementFile;

  const refreshBooking = () => {
    void queryClient.invalidateQueries({
      queryKey: getGetMyBookingQueryKey(eventId),
    });
  };

  const handleServicesAdded = (
    updated: BookingResponse,
    serviceIds: string[],
  ) => {
    refreshBooking();
    setPromptedServices(
      (updated.services ?? []).filter(
        (bookingService) =>
          serviceIds.includes(bookingService.service_id) &&
          bookingService.service.requirements.length > 0,
      ),
    );
  };

  const listedBookingServices = bookingServices.filter(
    (bookingService) =>
      !promptedServices.some((prompted) => prompted.id === bookingService.id),
  );

  const promptedChangeCount = promptedServices.filter((bookingService) =>
    bookingService.service.requirements.some(
      (requirement) =>
        requirementChangeKey(bookingService.id, requirement.id) in
        pendingRequirementChanges,
    ),
  ).length;

  const handleRequirementChange = (
    bookingServiceId: string,
    requirementId: string,
    change: PendingRequirementChange | null,
  ) => {
    setPendingRequirementChanges((current) => {
      const next = { ...current };
      const key = requirementChangeKey(bookingServiceId, requirementId);
      if (change === null) {
        delete next[key];
      } else {
        next[key] = change;
      }
      return next;
    });
  };

  const handleRequirementCompletionChange = useCallback(
    (bookingServiceId: string, requirementId: string, isComplete: boolean) => {
      setRequirementCompletion((current) => {
        const key = requirementChangeKey(bookingServiceId, requirementId);
        if (current[key] === isComplete) return current;
        return {
          ...current,
          [key]: isComplete,
        };
      });
    },
    [],
  );

  const navigateOrConfirmDiscard = (to: string) => {
    if (hasPendingRequirementChanges) {
      setPendingNavigationTo(to);
      return;
    }
    navigate(to);
  };

  const handleSaveRequirementChanges = async () => {
    const failedChanges: Record<string, PendingRequirementChange> = {};
    let savedCount = 0;

    for (const change of pendingRequirementChangeList) {
      const key = requirementChangeKey(
        change.bookingServiceId,
        change.requirementId,
      );
      try {
        if (change.kind === "text") {
          await saveRequirementText({
            bookingServiceId: change.bookingServiceId,
            requirementId: change.requirementId,
            data: { text_value: change.text },
          });
          await queryClient.invalidateQueries({
            queryKey: getGetBookingRequirementTextQueryKey(
              change.bookingServiceId,
              change.requirementId,
            ),
          });
          savedCount += 1;
          continue;
        }

        if (change.kind === "file") {
          await uploadRequirementFile({
            bookingServiceId: change.bookingServiceId,
            requirementId: change.requirementId,
            data: { file: change.file },
          });
        } else {
          await deleteRequirementFile({
            bookingServiceId: change.bookingServiceId,
            requirementId: change.requirementId,
          });
        }
        await queryClient.invalidateQueries({
          queryKey: getGetBookingRequirementFileQueryKey(
            change.bookingServiceId,
            change.requirementId,
          ),
        });
        savedCount += 1;
      } catch {
        failedChanges[key] = change;
      }
    }

    setPendingRequirementChanges(failedChanges);
    if (Object.keys(failedChanges).length === 0) {
      setConfirmRequirementsOpen(false);
      setPromptedServices([]);
      notifications.show({
        color: "green",
        message: t("kp.booking_manage.requirements_saved"),
      });
      return;
    }

    notifications.show({
      color: savedCount > 0 ? "yellow" : "red",
      message: t(
        savedCount > 0
          ? "kp.booking_manage.requirements_partially_saved"
          : "kp.booking_manage.requirements_save_failed",
        {
          failed: Object.keys(failedChanges).length,
          saved: savedCount,
        },
      ),
    });
  };

  if (isLoadingEvent || isLoadingBooking) {
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

  if (isInactiveBooking(booking)) {
    return <Navigate to={`/kp/${eventId}`} replace />;
  }

  return (
    <Stack gap="md">
      <Modal
        centered
        opened={pendingNavigationTo !== null}
        onClose={() => setPendingNavigationTo(null)}
        title={t("kp.booking_manage.discard_changes_title")}
      >
        <Stack gap="md">
          <Text size="sm">{t("kp.booking_manage.discard_changes_body")}</Text>
          <Group justify="flex-end">
            <Button
              variant="subtle"
              onClick={() => setPendingNavigationTo(null)}
            >
              {t("kp.booking_manage.stay_on_page")}
            </Button>
            <Button
              color="red"
              onClick={() => {
                const to = pendingNavigationTo;
                setPendingRequirementChanges({});
                setPendingNavigationTo(null);
                if (to) navigate(to);
              }}
            >
              {t("kp.booking_manage.discard_changes_submit")}
            </Button>
          </Group>
        </Stack>
      </Modal>
      <Modal
        centered
        opened={confirmRequirementsOpen}
        onClose={() => setConfirmRequirementsOpen(false)}
        title={t("kp.booking_manage.confirm_requirement_changes_title")}
      >
        <Stack gap="md">
          <Text size="sm">
            {t("kp.booking_manage.confirm_requirement_changes_body")}
          </Text>
          <Stack gap="xs">
            {pendingRequirementChangeList.map((change) => (
              <Group
                justify="space-between"
                key={requirementChangeKey(
                  change.bookingServiceId,
                  change.requirementId,
                )}
              >
                <div>
                  <Text size="sm" fw={600}>
                    {change.serviceName}
                  </Text>
                  <Text size="xs" c="dimmed">
                    {change.requirementName}
                  </Text>
                </div>
                <Badge variant="light">
                  {requirementChangeLabel(change, t)}
                </Badge>
              </Group>
            ))}
          </Stack>
          <Group justify="flex-end">
            <Button
              variant="subtle"
              onClick={() => setConfirmRequirementsOpen(false)}
            >
              {t("common.cancel")}
            </Button>
            <Button
              leftSection={<IconDeviceFloppy size={16} />}
              loading={isSavingRequirements}
              onClick={() => {
                void handleSaveRequirementChanges();
              }}
            >
              {t("kp.booking_manage.confirm_requirement_changes_submit")}
            </Button>
          </Group>
        </Stack>
      </Modal>
      <Modal
        centered
        size="xl"
        opened={promptedServices.length > 0}
        onClose={() => setPromptedServices([])}
        title={t("kp.booking_manage.requirements_prompt_title")}
      >
        <Stack gap="md">
          {promptedServices.map((bookingService) => (
            <BookedServiceCard
              bookingService={bookingService}
              completion={requirementCompletion}
              editable={isEditable}
              key={bookingService.id}
              onRequirementCompletionChange={handleRequirementCompletionChange}
              onRequirementChange={handleRequirementChange}
              pendingChanges={pendingRequirementChanges}
            />
          ))}
          <Group justify="flex-end">
            <Button variant="subtle" onClick={() => setPromptedServices([])}>
              {t("kp.booking_manage.requirements_prompt_later")}
            </Button>
            <Button
              disabled={promptedChangeCount === 0}
              leftSection={<IconDeviceFloppy size={16} />}
              loading={isSavingRequirements}
              onClick={() => {
                void handleSaveRequirementChanges();
              }}
            >
              {t("kp.booking_manage.requirements_prompt_save")}
            </Button>
          </Group>
        </Stack>
      </Modal>
      <ActionIcon
        aria-label={t("kp.booking_manage.back_to_manage")}
        radius="md"
        size="input-md"
        variant="transparent"
        onClick={() =>
          navigateOrConfirmDiscard(
            `/kp/${eventId}/booking/${booking.id}/manage`,
          )
        }
      >
        <IconArrowBackUp />
      </ActionIcon>
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
          onClick={() =>
            navigateOrConfirmDiscard(`/kp/${eventId}/booking/${booking.id}`)
          }
        >
          {t("kp.booking_manage.view_summary")}
        </Button>
      </Group>

      {!isEditable ? (
        <Alert icon={<IconAlertCircle />} color="yellow">
          {t("kp.booking_manage.readonly_notice")}
        </Alert>
      ) : null}

      <KpBookingCompletion
        booking={booking}
        changeDeadline={event.finalization_deadline}
      />

      {hasPendingRequirementChanges ? (
        <Alert icon={<IconAlertCircle />} color="yellow">
          {t("kp.booking_manage.unsaved_changes_notice", {
            count: pendingRequirementChangeList.length,
          })}
        </Alert>
      ) : null}

      <AddServicesForm
        bookingId={booking.id}
        bookingServices={bookingServices}
        editable={isEditable}
        eventId={eventId}
        onAdded={handleServicesAdded}
        vatRatePercent={event.vat_rate_percent}
      />

      <Stack gap="md">
        <div>
          <Group justify="space-between" align="flex-start">
            <div>
              <Title order={4}>
                {t("kp.booking_manage.requirements_title")}
              </Title>
              <Text c="dimmed" size="sm">
                {t("kp.booking_manage.requirements_description")}
              </Text>
            </div>
            <Badge
              color={allRequirementsComplete ? "green" : "yellow"}
              leftSection={
                allRequirementsComplete ? (
                  <IconCheck size={12} />
                ) : (
                  <IconProgressCheck size={12} />
                )
              }
              variant="light"
            >
              {totalRequirementCount
                ? t("kp.booking_manage.requirements_completed_count", {
                    completed: completedRequirementCount,
                    total: totalRequirementCount,
                  })
                : t("kp.booking_manage.no_requirements")}
            </Badge>
          </Group>
        </div>
        {!allRequirementsComplete ? (
          <Alert icon={<IconProgressCheck />} color="yellow">
            {t("kp.booking_manage.incomplete_requirements_notice")}
          </Alert>
        ) : null}
        {isEditable ? (
          <Group justify="flex-end">
            <Button
              leftSection={<IconDeviceFloppy size={16} />}
              disabled={!hasPendingRequirementChanges}
              loading={isSavingRequirements}
              onClick={() => setConfirmRequirementsOpen(true)}
            >
              {t("kp.booking_manage.save_requirement_changes", {
                count: pendingRequirementChangeList.length,
              })}
            </Button>
          </Group>
        ) : null}
        {bookingServices.length ? (
          <Stack gap="sm">
            {listedBookingServices.map((bookingService) => (
              <BookedServiceCard
                bookingService={bookingService}
                completion={requirementCompletion}
                editable={isEditable}
                key={bookingService.id}
                onRequirementCompletionChange={
                  handleRequirementCompletionChange
                }
                onRequirementChange={handleRequirementChange}
                pendingChanges={pendingRequirementChanges}
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
