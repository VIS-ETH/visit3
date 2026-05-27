import {
  Alert,
  Button,
  Card,
  Center,
  Grid,
  Group,
  Loader,
  Paper,
  Stack,
  Stepper,
  Text,
  Title,
} from "@mantine/core";
import {
  IconAlertCircle,
  IconCheck,
  IconClipboardList,
  IconInfoCircle,
  IconMap,
  IconMapPin,
} from "@tabler/icons-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";
import type {
  BookingResponse,
  BoothZoneWithAvailabilityResponse,
  KpResponse,
} from "../orval/generated/fastAPI.schemas";
import { useGetMyBooking } from "../orval/generated/kp/kp";
import { getEventStatus } from "../utils/kp-utils";
import type { BookingSummaryServiceLine } from "../components/KpBookingSummaryStep";
import KpBookingSummaryStep from "../components/KpBookingSummaryStep";
import KpBookingZoneSelector from "../components/KpBookingZoneSelector";

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

function KpBookingServicesStep() {
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
          <KpBookingServicesStep />
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
