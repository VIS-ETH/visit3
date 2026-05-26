import {
  Alert,
  Button,
  Card,
  Center,
  FileButton,
  Grid,
  Group,
  Image,
  Loader,
  NumberInput,
  Paper,
  SimpleGrid,
  Stack,
  Stepper,
  Text,
  Textarea,
  Title,
} from "@mantine/core";
import {
  IconAlertCircle,
  IconCheck,
  IconClipboardList,
  IconFile,
  IconFileTypePdf,
  IconInfoCircle,
  IconMap,
  IconMapPin,
  IconPhoto,
  IconTrash,
  IconUpload,
  IconVideo,
} from "@tabler/icons-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";
import { useListAvailableServices } from "../api/kp-services";
import { KpEventServiceRequirementType } from "../orval/generated/fastAPI.schemas";
import type {
  BookingResponse,
  BoothZoneWithAvailabilityResponse,
  KpResponse,
  ServiceRequirementResponse,
  ServiceResponse,
} from "../orval/generated/fastAPI.schemas";
import { useGetMyBooking } from "../orval/generated/kp/kp";
import { getEventStatus } from "../utils/kp-utils";
import type {
  BookingSummaryServiceLine,
  DraftBookingService,
} from "../components/KpBookingSummaryStep";
import KpBookingSummaryStep from "../components/KpBookingSummaryStep";
import KpBookingZoneSelector from "../components/KpBookingZoneSelector";
import { formatPrice } from "../utils/price-utils";

interface KpBookingStepperProps {
  event: KpResponse;
}

function KpBookingZoneStep({
  event,
  selectedZone,
  onSelectZone,
  myBooking,
  isLoadingBooking,
  isRegistrationOpen,
}: {
  event: KpResponse;
  selectedZone: BoothZoneWithAvailabilityResponse | null;
  onSelectZone: (zone: BoothZoneWithAvailabilityResponse | null) => void;
  myBooking: BookingResponse | null | undefined;
  isLoadingBooking: boolean;
  isRegistrationOpen: boolean;
}) {
  const { t } = useTranslation();

  if (isLoadingBooking) {
    return (
      <Center py="xl">
        <Loader />
      </Center>
    );
  }

  if (!isRegistrationOpen && !myBooking) {
    return (
      <Alert icon={<IconAlertCircle />} color="yellow" mt="xs">
        {t("kp.booking.registration_closed")}
      </Alert>
    );
  }

  return (
    <>
      <Grid mt="xs" gutter="lg">
        <Grid.Col span={{ base: 12, md: 7 }}>
          <Text fw={600} mb="sm">
            {t("kp.booking.venue_map_title")}
          </Text>
          <Paper
            withBorder
            radius="md"
            p="xl"
            style={{
              minHeight: 400,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              backgroundColor: "var(--visit-muted-bg)",
            }}
          >
            <IconMap size={64} style={{ opacity: 0.3, marginBottom: 16 }} />
            <Text c="dimmed" size="lg" fw={500}>
              {t("kp.booking.venue_map_title")}
            </Text>
            <Text c="dimmed" size="sm" ta="center" maw={300} mt="xs">
              {t("kp.booking.venue_map_placeholder")}
            </Text>
          </Paper>
        </Grid.Col>

        <Grid.Col span={{ base: 12, md: 5 }}>
          <Text fw={600} mb="sm">
            {t("kp.booking.select_zone")}
          </Text>
          <KpBookingZoneSelector
            eventId={event.id}
            currentBooking={myBooking}
            selectedZone={selectedZone}
            onSelectZone={onSelectZone}
          />
        </Grid.Col>
      </Grid>
    </>
  );
}

function KpBookingServicesStep({
  eventId,
  selectedServices,
  onChangeServices,
  onValidityChange,
}: {
  eventId: string;
  selectedServices: DraftBookingService[];
  onChangeServices: (services: DraftBookingService[]) => void;
  onValidityChange: (isValid: boolean) => void;
}) {
  const { t } = useTranslation();
  const { data: activeServices, isLoading } = useListAvailableServices(eventId);
  const selectedServiceById = new Map(
    selectedServices.map((service) => [service.serviceId, service]),
  );

  const updateQuantity = (service: ServiceResponse, quantity: number) => {
    const nextQuantity = Math.max(
      0,
      Math.min(quantity, service.max_quantity_per_booking),
    );
    const next = selectedServices.filter((item) => item.serviceId !== service.id);
    if (nextQuantity > 0) {
      const current = selectedServiceById.get(service.id);
      next.push({
        serviceId: service.id,
        quantity: nextQuantity,
        requirements: current?.requirements ?? {},
      });
    }
    onChangeServices(next);
  };

  const updateRequirement = (
    serviceId: string,
    requirementId: string,
    value: { text?: string; file?: File | null },
  ) => {
    onChangeServices(
      selectedServices.map((service) =>
        service.serviceId === serviceId
          ? {
              ...service,
              requirements: {
                ...(service.requirements ?? {}),
                [requirementId]: {
                  ...(service.requirements?.[requirementId] ?? {}),
                  ...value,
                },
              },
            }
          : service,
      ),
    );
  };

  const acceptForRequirement = (type: KpEventServiceRequirementType) => {
    if (type === KpEventServiceRequirementType.image) return "image/*";
    if (type === KpEventServiceRequirementType.pdf) return "application/pdf";
    if (type === KpEventServiceRequirementType.video) return "video/*";
    return undefined;
  };

  const iconForRequirement = (type: KpEventServiceRequirementType) => {
    if (type === KpEventServiceRequirementType.image) return <IconPhoto size={16} />;
    if (type === KpEventServiceRequirementType.pdf) {
      return <IconFileTypePdf size={16} />;
    }
    if (type === KpEventServiceRequirementType.video) return <IconVideo size={16} />;
    return <IconFile size={16} />;
  };

  const requirementUploadLabel = (type: KpEventServiceRequirementType) => {
    if (type === KpEventServiceRequirementType.image) {
      return t("kp.booking.requirement_upload_image");
    }
    if (type === KpEventServiceRequirementType.pdf) {
      return t("kp.booking.requirement_upload_pdf");
    }
    if (type === KpEventServiceRequirementType.video) {
      return t("kp.booking.requirement_upload_video");
    }
    return t("kp.booking.requirement_upload_file");
  };

  const requirementTypeLabel = (type: KpEventServiceRequirementType) => {
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

  const renderRequirementField = (
    service: ServiceResponse,
    requirement: ServiceRequirementResponse,
  ) => {
    const value = selectedServiceById.get(service.id)?.requirements?.[
      requirement.id
    ];
    if (requirement.type === KpEventServiceRequirementType.text) {
      return (
        <Textarea
          label={requirement.name}
          description={requirement.description}
          minRows={3}
          value={value?.text ?? ""}
          onChange={(event) =>
            updateRequirement(service.id, requirement.id, {
              text: event.currentTarget.value,
            })
          }
        />
      );
    }
    return (
      <Stack gap={4}>
        <Text size="sm" fw={500}>
          {requirement.name}
        </Text>
        <Text size="xs" c="dimmed">
          {requirement.description}
        </Text>
        <Group gap="xs" wrap="nowrap">
          <FileButton
            accept={acceptForRequirement(requirement.type)}
            onChange={(file) =>
              updateRequirement(service.id, requirement.id, { file })
            }
          >
            {(props) => (
              <Button
                {...props}
                leftSection={<IconUpload size={16} />}
                variant={value?.file ? "default" : "light"}
              >
                {value?.file
                  ? t("kp.booking.requirement_replace_file")
                  : requirementUploadLabel(requirement.type)}
              </Button>
            )}
          </FileButton>
          {value?.file ? (
            <>
              <Text size="sm" truncate="end">
                {value.file.name}
              </Text>
              <Button
                color="red"
                leftSection={<IconTrash size={16} />}
                onClick={() =>
                  updateRequirement(service.id, requirement.id, { file: null })
                }
                variant="subtle"
              >
                {t("kp.booking.requirement_clear_file")}
              </Button>
            </>
          ) : null}
        </Group>
      </Stack>
    );
  };

  useEffect(() => {
    const services = activeServices ?? [];
    const isValid = selectedServices.every((selectedService) => {
      const service = services.find((item) => item.id === selectedService.serviceId);
      if (!service) return true;
      return service.requirements.every((requirement) => {
        const value = selectedService.requirements?.[requirement.id];
        if (requirement.type === KpEventServiceRequirementType.text) {
          return Boolean(value?.text?.trim());
        }
        return Boolean(value?.file);
      });
    });
    onValidityChange(isValid);
  }, [activeServices, selectedServices, onValidityChange]);

  return (
    <Card withBorder radius="md" p="lg" mt="xs">
      <Group gap="sm" mb="sm">
        <IconClipboardList size={20} />
        <Title order={4}>{t("kp.booking.services_title")}</Title>
      </Group>

      <Alert icon={<IconInfoCircle />} color="orange" variant="light">
        <Text size="sm">{t("kp.booking.services_policy")}</Text>
      </Alert>
      {isLoading ? (
        <Center py="xl">
          <Loader />
        </Center>
      ) : (activeServices ?? []).length === 0 ? (
        <Text c="dimmed" size="sm" mt="md">
          {t("kp.booking.services_none_available")}
        </Text>
      ) : (
        <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md" mt="md">
          {(activeServices ?? []).map((service) => {
            const selectedService = selectedServiceById.get(service.id);
            const quantity = selectedService?.quantity ?? 0;
            return (
              <Paper withBorder radius="md" p="md" key={service.id}>
                <Stack gap="xs">
                  {service.image_url ? (
                    <Image
                      alt={service.name}
                      fit="cover"
                      h={96}
                      radius="sm"
                      src={service.image_url}
                    />
                  ) : null}
                  <Group justify="space-between" align="flex-start" wrap="nowrap">
                    <div style={{ minWidth: 0 }}>
                      <Text fw={600}>{service.name}</Text>
                      {service.description ? (
                        <Text c="dimmed" size="sm" mt={4}>
                          {service.description}
                        </Text>
                      ) : null}
                    </div>
                    <Text fw={600} size="sm" ta="right">
                      CHF {formatPrice(service.price)}
                    </Text>
                  </Group>
                  <NumberInput
                    label={t("kp.booking.service_quantity")}
                    min={0}
                    max={service.max_quantity_per_booking}
                    value={quantity}
                    onChange={(value) =>
                      updateQuantity(
                        service,
                        typeof value === "number" ? value : Number(value) || 0,
                      )
                    }
                  />
                  {service.max_total_quantity > 0 ? (
                    <Text c="dimmed" size="xs">
                      {t("kp.booking.service_limited_total", {
                        total: service.max_total_quantity,
                      })}
                    </Text>
                  ) : null}
                  {quantity > 0 && service.requirements.length > 0 ? (
                    <Stack gap="sm" mt="xs">
                      <Text size="sm" fw={600}>
                        {t("kp.booking.service_requirements")}
                      </Text>
                      {service.requirements
                        .slice()
                        .sort((a, b) => a.order - b.order)
                        .map((requirement) => (
                          <Paper
                            withBorder
                            radius="sm"
                            p="sm"
                            key={requirement.id}
                          >
                            <Group gap="xs" mb="xs">
                              {iconForRequirement(requirement.type)}
                              <Text size="xs" c="dimmed">
                                {requirementTypeLabel(requirement.type)}
                              </Text>
                            </Group>
                            {renderRequirementField(service, requirement)}
                          </Paper>
                        ))}
                    </Stack>
                  ) : null}
                </Stack>
              </Paper>
            );
          })}
        </SimpleGrid>
      )}
    </Card>
  );
}

const KpBookingStepper = ({ event }: KpBookingStepperProps) => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [activeStep, setActiveStep] = useState(0);
  const [selectedZone, setSelectedZone] =
    useState<BoothZoneWithAvailabilityResponse | null>(null);
  const [draftAdditionalServiceLines, setDraftAdditionalServiceLines] =
    useState<BookingSummaryServiceLine[]>([]);
  const [draftServices, setDraftServices] = useState<DraftBookingService[]>([]);
  const [servicesStepValid, setServicesStepValid] = useState(true);
  const summaryConfirmActionRef = useRef<(() => void) | null>(null);
  const [summaryConfirmUiState, setSummaryConfirmUiState] = useState({
    visible: false,
    disabled: true,
    loading: false,
  });

  const isRegistrationOpen = getEventStatus(event) === "registration_open";
  const { data: myBooking, isLoading: isLoadingBooking } = useGetMyBooking(
    event.id,
  );

  useEffect(() => {
    setDraftAdditionalServiceLines([]);
    setDraftServices([]);
    setServicesStepValid(true);
  }, [selectedZone?.id]);

  const handleSummaryConfirmStateChange = useCallback(
    (
      state: {
        onConfirm: () => void;
        disabled: boolean;
        loading: boolean;
      } | null,
    ) => {
      summaryConfirmActionRef.current = state?.onConfirm ?? null;
      setSummaryConfirmUiState((prev) => {
        const next = {
          visible: Boolean(state),
          disabled: state?.disabled ?? true,
          loading: state?.loading ?? false,
        };
        if (
          prev.visible === next.visible &&
          prev.disabled === next.disabled &&
          prev.loading === next.loading
        ) {
          return prev;
        }
        return next;
      });
    },
    [],
  );

  if (myBooking) {
    return (
      <Card withBorder radius="md" p="lg" mt="xs">
        <Stack gap="md">
          <Alert icon={<IconCheck size={18} />} color="green" variant="light">
            You already have a booking for this event.
          </Alert>
          <Group justify="flex-end">
            <Button
              onClick={() =>
                navigate(`/kp/${event.id}/booking/${myBooking.id}`)
              }
            >
              {t("kp.company_view.manage_booking")}
            </Button>
          </Group>
        </Stack>
      </Card>
    );
  }

  const canContinueFromZone =
    Boolean(selectedZone) &&
    (selectedZone?.available_spots ?? 0) > 0 &&
    (isRegistrationOpen || Boolean(myBooking));

  const backLabel =
    activeStep === 0
      ? t("kp.booking.stepper_back_overview")
      : t("kp.booking.stepper_back");
  const onBack =
    activeStep === 0
      ? () => navigate(`/kp/${event.id}`)
      : () => setActiveStep((s) => Math.max(0, s - 1));

  const showForward =
    activeStep < 2 || (activeStep === 2 && summaryConfirmUiState.visible);

  let forwardLabel = "";
  let forwardDisabled = false;
  let forwardLoading = false;
  let onForward: () => void = () => {};

  if (activeStep === 0) {
    forwardLabel = selectedZone
      ? t("kp.booking.continue_with_zone", { zone: selectedZone.name })
      : t("kp.booking.stepper_continue");
    forwardDisabled = !canContinueFromZone || isLoadingBooking;
    onForward = () => setActiveStep(1);
  } else if (activeStep === 1) {
    forwardLabel = t("kp.booking.continue_to_summary");
    forwardDisabled = !servicesStepValid;
    onForward = () => setActiveStep(2);
  } else if (activeStep === 2 && summaryConfirmUiState.visible) {
    forwardLabel = t("kp.booking.summary_confirm_register");
    forwardDisabled = summaryConfirmUiState.disabled;
    forwardLoading = summaryConfirmUiState.loading;
    onForward = () => summaryConfirmActionRef.current?.();
  }

  return (
    <Stack gap="sm">
      <Stepper
        active={activeStep}
        onStepClick={(step) => {
          if (step <= activeStep) setActiveStep(step);
        }}
        contentPadding="xs"
      >
        <Stepper.Step
          label={t("kp.booking.step_zone")}
          icon={<IconMapPin size={18} />}
        >
          <KpBookingZoneStep
            event={event}
            selectedZone={selectedZone}
            onSelectZone={setSelectedZone}
            myBooking={myBooking}
            isLoadingBooking={isLoadingBooking}
            isRegistrationOpen={isRegistrationOpen}
          />
        </Stepper.Step>
        <Stepper.Step
          label={t("kp.booking.step_services")}
          icon={<IconClipboardList size={18} />}
        >
          <KpBookingServicesStep
            eventId={event.id}
            selectedServices={draftServices}
            onValidityChange={setServicesStepValid}
            onChangeServices={(services) => {
              setDraftServices(services);
              setDraftAdditionalServiceLines([]);
            }}
          />
        </Stepper.Step>
        <Stepper.Step
          label={t("kp.booking.step_summary")}
          icon={<IconCheck size={18} />}
        >
          <KpBookingSummaryStep
            eventId={event.id}
            isLoadingBooking={isLoadingBooking}
            draftZone={selectedZone}
            isRegistrationOpen={isRegistrationOpen}
            draftAdditionalServiceLines={draftAdditionalServiceLines}
            draftServices={draftServices}
            onConfirmStateChange={handleSummaryConfirmStateChange}
          />
        </Stepper.Step>
      </Stepper>

      <Group
        justify={showForward ? "space-between" : "flex-start"}
        wrap="nowrap"
        align="center"
      >
        <Button variant="default" size="md" maw={340} onClick={onBack}>
          {backLabel}
        </Button>
        {showForward ? (
          <Button
            size="md"
            maw={340}
            disabled={forwardDisabled}
            loading={forwardLoading}
            onClick={onForward}
          >
            {forwardLabel}
          </Button>
        ) : null}
      </Group>
    </Stack>
  );
};
export default KpBookingStepper;
