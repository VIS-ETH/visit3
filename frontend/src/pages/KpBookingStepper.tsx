import {
  Alert,
  Anchor,
  Badge,
  Button,
  Card,
  Center,
  Checkbox,
  FileButton,
  Grid,
  Group,
  Image,
  List,
  Loader,
  NumberInput,
  Paper,
  SimpleGrid,
  Stack,
  Stepper,
  Switch,
  Text,
  Textarea,
  ThemeIcon,
  Title,
  Tooltip,
} from "@mantine/core";
import {
  IconAlertCircle,
  IconArmchair,
  IconBuilding,
  IconCheck,
  IconClipboardList,
  IconExternalLink,
  IconFile,
  IconFileTypePdf,
  IconInfoCircle,
  IconMapPin,
  IconPhoto,
  IconTrash,
  IconUpload,
  IconVideo,
} from "@tabler/icons-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { NavLink, useNavigate } from "react-router";
import {
  KpEventServiceRequirementType,
  KpServiceCategory,
} from "../orval/generated/fastAPI.schemas";
import type {
  BookingResponse,
  BoothZoneWithAvailabilityResponse,
  CompanyProfileResponse,
  IncludedServiceResponse,
  KpResponse,
  MyCompanyResponse,
  ServiceRequirementResponse,
  ServiceResponse,
} from "../orval/generated/fastAPI.schemas";
import {
  useGetMyCompany,
  useGetMyCompanyProfile,
} from "../orval/generated/company/company";
import {
  useGetMyBooking,
  useListAvailableServices,
} from "../orval/generated/kp/kp";
import { getEventStatus } from "../utils/kp-utils";
import { activeBooking } from "../utils/my-booking";
import type {
  BookingConfirmState,
  DraftBookingRequirementValue,
  DraftBookingService,
} from "../components/KpBookingSummaryStep";
import KpBookingSummaryStep from "../components/KpBookingSummaryStep";
import KpBookingZoneSelector from "../components/KpBookingZoneSelector";
import VenueZonePicker from "../components/venue/VenueZonePicker";
import {
  chargedServiceQuantity,
  clampServiceQuantity,
  includedQuantitiesByServiceId,
  maxServiceQuantity,
  servicesOfCategory,
} from "../utils/kp-service-quantity";
import { COMPANY_PROFILE_PATH } from "../utils/navigation";
import { formatPrice } from "../utils/price-utils";
import {
  acceptForRequirement,
  allowedFormatsLabel,
  isPdfSource,
} from "../utils/upload-formats";

const NO_INCLUDED_SERVICES: IncludedServiceResponse[] = [];
const NO_SERVICES: ServiceResponse[] = [];

interface KpBookingStepperProps {
  event: KpResponse;
}

const joinProfileParts = (parts: (string | null | undefined)[]) =>
  parts
    .map((part) => part?.trim())
    .filter((part): part is string => Boolean(part));

const billingAddressLines = (profile: CompanyProfileResponse) =>
  joinProfileParts([
    profile.billing_company_name,
    joinProfileParts([
      profile.billing_street,
      profile.billing_house_number,
    ]).join(" "),
    joinProfileParts([profile.billing_postal_code, profile.billing_city]).join(
      " ",
    ),
    profile.billing_country,
  ]);

const isRequirementAnswered = (
  requirement: ServiceRequirementResponse,
  value: DraftBookingRequirementValue | undefined,
) =>
  requirement.type === KpEventServiceRequirementType.text
    ? Boolean(value?.text?.trim())
    : Boolean(value?.file);

function ProfileSummaryField({
  label,
  lines,
}: {
  label: string;
  lines: string[];
}) {
  const { t } = useTranslation();
  return (
    <Stack gap={2}>
      <Text c="dimmed" size="xs">
        {label}
      </Text>
      {lines.length === 0 ? (
        <Text size="sm">{t("kp.booking.profile_value_missing")}</Text>
      ) : (
        lines.map((line) => (
          <Text key={line} size="sm">
            {line}
          </Text>
        ))
      )}
    </Stack>
  );
}

function KpBookingProfileStep({
  company,
  isConfirmed,
  onConfirmedChange,
}: {
  company: MyCompanyResponse | undefined;
  isConfirmed: boolean;
  onConfirmedChange: (isConfirmed: boolean) => void;
}) {
  const { t } = useTranslation();
  const { data: profile, isLoading } = useGetMyCompanyProfile();
  const missingFields = company?.missing_profile_fields ?? [];

  if (isLoading || !profile || !company) {
    return (
      <Center py="xl">
        <Loader />
      </Center>
    );
  }

  return (
    <Card withBorder radius="md" p="lg" mt="xs">
      <Stack gap="md">
        <Group gap="sm">
          <IconBuilding size={20} />
          <Title order={4}>{t("kp.booking.profile_title")}</Title>
        </Group>
        <Text c="dimmed" size="sm">
          {t("kp.booking.profile_description")}
        </Text>
        <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
          <ProfileSummaryField
            label={t("kp.booking.profile_company")}
            lines={joinProfileParts([company.name, profile.brand_name])}
          />
          <ProfileSummaryField
            label={t("kp.booking.profile_contact")}
            lines={joinProfileParts([
              profile.contact_person,
              profile.contact_email,
              profile.contact_phone,
            ])}
          />
          <ProfileSummaryField
            label={t("kp.booking.profile_billing_address")}
            lines={billingAddressLines(profile)}
          />
          <ProfileSummaryField
            label={t("kp.booking.profile_industries")}
            lines={(profile.industries ?? []).map((industry) => industry.name)}
          />
        </SimpleGrid>
        {missingFields.length > 0 ? (
          <Alert icon={<IconAlertCircle />} color="yellow">
            <Stack gap="xs">
              <Text size="sm">{t("kp.booking.profile_incomplete")}</Text>
              <List size="sm" withPadding>
                {missingFields.map((field) => (
                  <List.Item key={field}>
                    {t(`kp.booking.profile_field.${field}`)}
                  </List.Item>
                ))}
              </List>
              <Anchor component={NavLink} size="sm" to={COMPANY_PROFILE_PATH}>
                {t("kp.booking.profile_open")}
              </Anchor>
            </Stack>
          </Alert>
        ) : null}
        <Checkbox
          checked={isConfirmed}
          disabled={!company.profile_complete}
          label={t("kp.booking.profile_confirm_checkbox")}
          onChange={(event) => onConfirmedChange(event.currentTarget.checked)}
        />
      </Stack>
    </Card>
  );
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
      <Grid mt="xs" gap="lg">
        <Grid.Col span={{ base: 12, md: 7 }}>
          <Text fw={600} mb="sm">
            {t("kp.booking.venue_map_title")}
          </Text>
          <VenueZonePicker
            eventId={event.id}
            onSelectZone={onSelectZone}
            selectedZone={selectedZone}
          />
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

function KpBookingServiceGrid({
  services,
  includedQuantities,
  selectedServices,
  onChangeServices,
  emptyLabel,
  isLoading,
}: {
  services: ServiceResponse[];
  includedQuantities: Map<string, number>;
  selectedServices: DraftBookingService[];
  onChangeServices: (services: DraftBookingService[]) => void;
  emptyLabel: string;
  isLoading: boolean;
}) {
  const { t } = useTranslation();
  const includedFor = (serviceId: string) =>
    includedQuantities.get(serviceId) ?? 0;
  const selectedServiceById = new Map(
    selectedServices.map((service) => [service.serviceId, service]),
  );

  const updateQuantity = (service: ServiceResponse, quantity: number) => {
    const nextQuantity = clampServiceQuantity(
      service,
      includedFor(service.id),
      quantity,
    );
    const next = selectedServices.filter(
      (item) => item.serviceId !== service.id,
    );
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
    value: DraftBookingRequirementValue,
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

  const iconForRequirement = (type: KpEventServiceRequirementType) => {
    if (type === KpEventServiceRequirementType.image)
      return <IconPhoto size={16} />;
    if (type === KpEventServiceRequirementType.pdf) {
      return <IconFileTypePdf size={16} />;
    }
    if (type === KpEventServiceRequirementType.video)
      return <IconVideo size={16} />;
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
        <Text size="xs" c="dimmed">
          {allowedFormatsLabel(requirement.type, t)}
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

  if (isLoading) {
    return (
      <Center py="xl">
        <Loader />
      </Center>
    );
  }

  if (services.length === 0) {
    return (
      <Text c="dimmed" size="sm" mt="md">
        {emptyLabel}
      </Text>
    );
  }

  return (
    <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md" mt="md">
      {services.map((service, index) => {
        const selectedService = selectedServiceById.get(service.id);
        const included = includedFor(service.id);
        const quantity = selectedService?.quantity ?? included;
        const charged = chargedServiceQuantity(quantity, included);
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
                <Stack gap={4} align="flex-end">
                  <Group gap={6} wrap="nowrap">
                    <Text fw={600} size="sm" ta="right">
                      CHF {formatPrice(service.price)}
                    </Text>
                    {index === 0 ? (
                      <Tooltip
                        multiline
                        w={240}
                        label={t("kp.booking.price_excl_vat_hint")}
                      >
                        <ThemeIcon
                          aria-label={t("kp.booking.price_excl_vat_hint")}
                          color="gray"
                          size="sm"
                          variant="subtle"
                        >
                          <IconInfoCircle size={16} />
                        </ThemeIcon>
                      </Tooltip>
                    ) : null}
                  </Group>
                  {included > 0 ? (
                    <Badge color="green" variant="light">
                      {t("kp.booking.service_included_note", { included })}
                    </Badge>
                  ) : null}
                </Stack>
              </Group>
              {service.max_quantity_per_booking === 1 ? (
                <Switch
                  checked={quantity > 0}
                  disabled={maxServiceQuantity(service, included) <= included}
                  label={t("kp.booking.service_book_toggle")}
                  onChange={(event) =>
                    updateQuantity(service, event.currentTarget.checked ? 1 : 0)
                  }
                />
              ) : (
                <NumberInput
                  allowDecimal={false}
                  allowNegative={false}
                  clampBehavior="strict"
                  description={t("kp.booking.service_max_per_booking", {
                    max: service.max_quantity_per_booking,
                  })}
                  label={
                    service.unit_label
                      ? t("kp.booking.service_quantity_with_unit", {
                          unit: service.unit_label,
                        })
                      : t("kp.booking.service_quantity")
                  }
                  min={included}
                  max={maxServiceQuantity(service, included)}
                  step={1}
                  value={quantity}
                  onChange={(value) =>
                    updateQuantity(
                      service,
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
              {quantity > 0 ? (
                <Group justify="space-between" wrap="nowrap">
                  <Text size="sm" c="dimmed">
                    {t("kp.booking.service_line_total")}
                  </Text>
                  <Text fw={600} size="sm">
                    CHF {formatPrice(service.price * charged)}
                  </Text>
                </Group>
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
                      <Paper withBorder radius="sm" p="sm" key={requirement.id}>
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
  );
}

function KpBookingServicesStep(props: {
  services: ServiceResponse[];
  includedQuantities: Map<string, number>;
  selectedServices: DraftBookingService[];
  onChangeServices: (services: DraftBookingService[]) => void;
  isLoading: boolean;
}) {
  const { t } = useTranslation();

  return (
    <Card withBorder radius="md" p="lg" mt="xs">
      <Group gap="sm" mb="sm">
        <IconClipboardList size={20} />
        <Title order={4}>{t("kp.booking.services_title")}</Title>
      </Group>

      <Alert icon={<IconInfoCircle />} color="orange" variant="light">
        <Text size="sm">{t("kp.booking.services_policy")}</Text>
      </Alert>
      <KpBookingServiceGrid
        {...props}
        emptyLabel={t("kp.booking.services_none_available")}
      />
    </Card>
  );
}

function KpBoothLayoutCard({
  zone,
}: {
  zone: BoothZoneWithAvailabilityResponse | null;
}) {
  const { t } = useTranslation();
  const layoutUrl = zone?.layout_url ?? null;
  const layoutDescription = zone?.layout_description ?? null;

  return (
    <Card withBorder radius="md" p="lg">
      <Stack gap="sm">
        <Title order={5}>{t("kp.booking.booth_layout_title")}</Title>
        {layoutDescription ? <Text size="sm">{layoutDescription}</Text> : null}
        {layoutUrl ? (
          isPdfSource(layoutUrl) ? (
            <Anchor href={layoutUrl} target="_blank" rel="noopener noreferrer">
              <Group gap={6} wrap="nowrap">
                <IconExternalLink size={16} />
                <Text size="sm">{t("kp.booking.booth_layout_open_pdf")}</Text>
              </Group>
            </Anchor>
          ) : (
            <Image
              alt={t("kp.booking.booth_layout_preview_alt")}
              fit="contain"
              radius="sm"
              src={layoutUrl}
            />
          )
        ) : null}
        {!layoutDescription && !layoutUrl ? (
          <Text c="dimmed" size="sm">
            {t("kp.booking.booth_layout_none")}
          </Text>
        ) : null}
      </Stack>
    </Card>
  );
}

function KpBookingBoothStep({
  zone,
  ...gridProps
}: {
  zone: BoothZoneWithAvailabilityResponse | null;
  services: ServiceResponse[];
  includedQuantities: Map<string, number>;
  selectedServices: DraftBookingService[];
  onChangeServices: (services: DraftBookingService[]) => void;
  isLoading: boolean;
}) {
  const { t } = useTranslation();

  return (
    <Grid mt="xs" gap="lg">
      <Grid.Col span={{ base: 12, md: 8 }}>
        <Card withBorder radius="md" p="lg">
          <Group gap="sm" mb="sm">
            <IconArmchair size={20} />
            <Title order={4}>{t("kp.booking.booth_title")}</Title>
          </Group>
          <Text c="dimmed" size="sm">
            {t("kp.booking.booth_description")}
          </Text>
          <KpBookingServiceGrid
            {...gridProps}
            emptyLabel={t("kp.booking.booth_none_available")}
          />
        </Card>
      </Grid.Col>
      <Grid.Col span={{ base: 12, md: 4 }}>
        <KpBoothLayoutCard zone={zone} />
      </Grid.Col>
    </Grid>
  );
}

const KpBookingStepper = ({ event }: KpBookingStepperProps) => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [activeStep, setActiveStep] = useState(0);
  const [isProfileConfirmed, setIsProfileConfirmed] = useState(false);
  const [selectedZone, setSelectedZone] =
    useState<BoothZoneWithAvailabilityResponse | null>(null);
  const [draftServices, setDraftServices] = useState<DraftBookingService[]>([]);
  const summaryConfirmActionRef = useRef<(() => Promise<void>) | null>(null);
  const [isConfirmingBooking, setIsConfirmingBooking] = useState(false);
  const [summaryConfirmUiState, setSummaryConfirmUiState] = useState({
    visible: false,
    disabled: true,
    loading: false,
  });

  const isRegistrationOpen = getEventStatus(event) === "registration_open";
  const { data: latestBooking, isLoading: isLoadingBooking } = useGetMyBooking(
    event.id,
  );
  const myBooking = activeBooking(latestBooking);
  const { data: company } = useGetMyCompany();
  const { data: availableServices, isLoading: isLoadingServices } =
    useListAvailableServices(event.id);
  const allServices = availableServices ?? NO_SERVICES;
  const includedQuantities = useMemo(
    () =>
      includedQuantitiesByServiceId(
        selectedZone?.included_services ?? NO_INCLUDED_SERVICES,
      ),
    [selectedZone],
  );
  const bookableServices = useMemo(
    () => servicesOfCategory(allServices, KpServiceCategory.SERVICE),
    [allServices],
  );
  const boothElements = useMemo(
    () => servicesOfCategory(allServices, KpServiceCategory.BOOTH_ELEMENT),
    [allServices],
  );

  useEffect(() => {
    setDraftServices([]);
  }, [selectedZone?.id]);

  useEffect(() => {
    if (allServices.length === 0) return;
    const clamped = draftServices.map((selected) => {
      const service = allServices.find(
        (item) => item.id === selected.serviceId,
      );
      if (!service) return selected;
      const quantity = clampServiceQuantity(
        service,
        includedQuantities.get(service.id) ?? 0,
        selected.quantity,
      );
      return quantity === selected.quantity
        ? selected
        : { ...selected, quantity };
    });
    const seeded = allServices.flatMap((service) => {
      const included = includedQuantities.get(service.id) ?? 0;
      if (included === 0) return [];
      if (clamped.some((item) => item.serviceId === service.id)) return [];
      return [
        {
          serviceId: service.id,
          quantity: clampServiceQuantity(service, included, included),
          requirements: {},
        },
      ];
    });
    const isUnchanged =
      seeded.length === 0 &&
      clamped.every((item, index) => item === draftServices[index]);
    if (isUnchanged) return;
    setDraftServices([...clamped, ...seeded]);
  }, [allServices, includedQuantities, draftServices]);

  const isCategoryComplete = (category: KpServiceCategory) =>
    draftServices.every((selected) => {
      const service = allServices.find(
        (item) => item.id === selected.serviceId,
      );
      if (service?.category !== category) return true;
      return service.requirements.every((requirement) =>
        isRequirementAnswered(
          requirement,
          selected.requirements?.[requirement.id],
        ),
      );
    });

  const handleSummaryConfirmStateChange = useCallback(
    (state: BookingConfirmState | null) => {
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
            {t("kp.booking.already_booked_notice")}
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

  const canContinueFromProfile =
    Boolean(company?.profile_complete) && isProfileConfirmed;
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
    activeStep < 4 || (activeStep === 4 && summaryConfirmUiState.visible);

  const confirmBooking = async () => {
    const confirm = summaryConfirmActionRef.current;
    if (!confirm || isConfirmingBooking) return;
    setIsConfirmingBooking(true);
    try {
      await confirm();
    } finally {
      setIsConfirmingBooking(false);
    }
  };

  let forwardLabel = "";
  let forwardDisabled = false;
  let forwardLoading = false;
  let onForward: () => void | Promise<void> = () => {};

  if (activeStep === 0) {
    forwardLabel = t("kp.booking.continue_to_zone");
    forwardDisabled = !canContinueFromProfile;
    onForward = () => setActiveStep(1);
  } else if (activeStep === 1) {
    forwardLabel = selectedZone
      ? t("kp.booking.continue_with_zone", { zone: selectedZone.name })
      : t("kp.booking.stepper_continue");
    forwardDisabled = !canContinueFromZone || isLoadingBooking;
    onForward = () => setActiveStep(2);
  } else if (activeStep === 2) {
    forwardLabel = t("kp.booking.continue_to_booth");
    forwardDisabled = !isCategoryComplete(KpServiceCategory.SERVICE);
    onForward = () => setActiveStep(3);
  } else if (activeStep === 3) {
    forwardLabel = t("kp.booking.continue_to_summary");
    forwardDisabled = !isCategoryComplete(KpServiceCategory.BOOTH_ELEMENT);
    onForward = () => setActiveStep(4);
  } else if (activeStep === 4 && summaryConfirmUiState.visible) {
    forwardLabel = t("kp.booking.summary_confirm_register");
    forwardDisabled = summaryConfirmUiState.disabled || isConfirmingBooking;
    forwardLoading = summaryConfirmUiState.loading || isConfirmingBooking;
    onForward = confirmBooking;
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
          label={t("kp.booking.step_profile")}
          icon={<IconBuilding size={18} />}
        >
          <KpBookingProfileStep
            company={company}
            isConfirmed={isProfileConfirmed}
            onConfirmedChange={setIsProfileConfirmed}
          />
        </Stepper.Step>
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
            services={bookableServices}
            includedQuantities={includedQuantities}
            selectedServices={draftServices}
            onChangeServices={setDraftServices}
            isLoading={isLoadingServices}
          />
        </Stepper.Step>
        <Stepper.Step
          label={t("kp.booking.step_booth")}
          icon={<IconArmchair size={18} />}
        >
          <KpBookingBoothStep
            zone={selectedZone}
            services={boothElements}
            includedQuantities={includedQuantities}
            selectedServices={draftServices}
            onChangeServices={setDraftServices}
            isLoading={isLoadingServices}
          />
        </Stepper.Step>
        <Stepper.Step
          label={t("kp.booking.step_summary")}
          icon={<IconCheck size={18} />}
        >
          <KpBookingSummaryStep
            eventId={event.id}
            isLoadingBooking={isLoadingBooking}
            isProfileConfirmed={isProfileConfirmed}
            vatRatePercent={event.vat_rate_percent}
            termsUrl={event.terms_url}
            draftZone={selectedZone}
            isRegistrationOpen={isRegistrationOpen}
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
            onClick={() => {
              void onForward();
            }}
          >
            {forwardLabel}
          </Button>
        ) : null}
      </Group>
    </Stack>
  );
};
export default KpBookingStepper;
