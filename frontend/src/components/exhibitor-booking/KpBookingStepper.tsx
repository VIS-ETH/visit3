import { Alert, Button, Card, Group, Stack, Stepper } from "@mantine/core";
import {
  IconArmchair,
  IconBuilding,
  IconCheck,
  IconClipboardList,
  IconMapPin,
} from "@tabler/icons-react";
import { useCallback, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";
import { KpServiceCategory } from "../../orval/generated/fastAPI.schemas";
import type {
  KpResponse,
  ServiceResponse,
} from "../../orval/generated/fastAPI.schemas";
import { useGetMyCompany } from "../../orval/generated/company/company";
import {
  useGetMyBooking,
  useListAvailableServices,
} from "../../orval/generated/kp/kp";
import { useAsyncAction } from "../../hooks/use-async-action";
import { getEventStatus } from "../../utils/kp-utils";
import { activeBooking } from "../../utils/my-booking";
import { servicesOfCategory } from "../../utils/kp-service-quantity";
import { isZoneBookable } from "../../utils/booth-zones";
import ErrorAlert from "../ErrorAlert";
import type { BookingConfirmState } from "./KpBookingSummaryStep";
import KpBookingSummaryStep from "./KpBookingSummaryStep";
import BookingProfileConfirmation from "./BookingProfileConfirmation";
import KpBookingZoneStep from "./stepper/KpBookingZoneStep";
import KpBookingServicesStep from "./stepper/KpBookingServicesStep";
import KpBookingBoothStep from "./stepper/KpBookingBoothStep";
import { useBookingDraft } from "./stepper/use-booking-draft";

const NO_SERVICES: ServiceResponse[] = [];

interface KpBookingStepperProps {
  event: KpResponse;
}

const KpBookingStepper = ({ event }: KpBookingStepperProps) => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [activeStep, setActiveStep] = useState(0);
  const [isProfileConfirmed, setIsProfileConfirmed] = useState(false);
  const summaryConfirmActionRef = useRef<(() => Promise<void>) | null>(null);
  const [summaryConfirmUiState, setSummaryConfirmUiState] = useState({
    visible: false,
    disabled: true,
    loading: false,
  });

  const isRegistrationOpen = getEventStatus(event) === "registration_open";
  const bookingQuery = useGetMyBooking(event.id);
  const latestBooking = bookingQuery.data;
  const isLoadingBooking = bookingQuery.isLoading;
  const isBookingError = bookingQuery.isError && latestBooking === undefined;
  const myBooking = activeBooking(latestBooking);
  const companyQuery = useGetMyCompany();
  const company = companyQuery.data;
  const servicesQuery = useListAvailableServices(event.id);
  const availableServices = servicesQuery.data;
  const allServices = availableServices ?? NO_SERVICES;
  const {
    selectedZone,
    selectZone,
    draftServices,
    setDraftServices,
    includedQuantities,
    excludedBy,
  } = useBookingDraft(allServices);
  const bookableServices = useMemo(
    () => servicesOfCategory(allServices, KpServiceCategory.SERVICE),
    [allServices],
  );
  const boothElements = useMemo(
    () => servicesOfCategory(allServices, KpServiceCategory.BOOTH_ELEMENT),
    [allServices],
  );
  const { run: confirmBooking, isRunning: isConfirmingBooking } =
    useAsyncAction(async () => {
      await summaryConfirmActionRef.current?.();
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
    Boolean(company?.profile_bookable) &&
    Boolean(company?.confirmed_at) &&
    isProfileConfirmed;
  const canContinueFromZone =
    selectedZone !== null &&
    isZoneBookable(selectedZone) &&
    isRegistrationOpen &&
    !isBookingError;

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

  let forwardLabel = "";
  let forwardDisabled = false;
  let forwardLoading = false;
  let onForward: () => void | Promise<unknown> = () => {};

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
    onForward = () => setActiveStep(3);
  } else if (activeStep === 3) {
    forwardLabel = t("kp.booking.continue_to_summary");
    onForward = () => setActiveStep(4);
  } else if (activeStep === 4 && summaryConfirmUiState.visible) {
    forwardLabel = t("kp.booking.summary_confirm_register");
    forwardDisabled = summaryConfirmUiState.disabled || isConfirmingBooking;
    forwardLoading = summaryConfirmUiState.loading || isConfirmingBooking;
    onForward = confirmBooking;
  }

  const serviceStepProps = {
    allServices,
    includedQuantities,
    excludedBy,
    selectedServices: draftServices,
    onChangeServices: setDraftServices,
    isLoading: servicesQuery.isLoading,
    isError: servicesQuery.isError && !availableServices,
  };

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
          {companyQuery.isError && !company ? (
            <ErrorAlert />
          ) : (
            <BookingProfileConfirmation
              returnPath={`/kp/${event.id}/booking`}
              company={company}
              isConfirmed={isProfileConfirmed}
              onConfirmedChange={setIsProfileConfirmed}
            />
          )}
        </Stepper.Step>
        <Stepper.Step
          label={t("kp.booking.step_zone")}
          icon={<IconMapPin size={18} />}
        >
          <KpBookingZoneStep
            event={event}
            selectedZone={selectedZone}
            onSelectZone={selectZone}
            myBooking={myBooking}
            isLoadingBooking={isLoadingBooking}
            isBookingError={isBookingError}
            isRegistrationOpen={isRegistrationOpen}
          />
        </Stepper.Step>
        <Stepper.Step
          label={t("kp.booking.step_services")}
          icon={<IconClipboardList size={18} />}
        >
          <KpBookingServicesStep
            {...serviceStepProps}
            services={bookableServices}
          />
        </Stepper.Step>
        <Stepper.Step
          label={t("kp.booking.step_booth")}
          icon={<IconArmchair size={18} />}
        >
          <KpBookingBoothStep {...serviceStepProps} services={boothElements} />
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
