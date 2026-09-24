import {
  Alert,
  Anchor,
  Card,
  Center,
  Checkbox,
  Group,
  Loader,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconAlertCircle } from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";
import { getApiErrorCode } from "../api/errors";
import { KpServiceCategory } from "../orval/generated/fastAPI.schemas";
import type {
  BookingResponse,
  BoothZoneWithAvailabilityResponse,
  RegisterBookingRequest,
} from "../orval/generated/fastAPI.schemas";
import {
  getGetMyBookingQueryKey,
  getListAvailableBoothZonesQueryKey,
  getMyBooking,
  useListAvailableServices,
  useRegisterBooking,
  useUpsertBookingRequirementText,
  useUploadBookingRequirementFile,
} from "../orval/generated/kp/kp";
import {
  chargedServiceQuantity,
  includedQuantitiesByServiceId,
  serviceLineLabel,
} from "../utils/kp-service-quantity";
import { activeBooking } from "../utils/my-booking";
import { formatPrice } from "../utils/price-utils";
import { priceBreakdown } from "../utils/pricing";
import SummaryPriceBreakdown from "./SummaryPriceBreakdown";

const BOOKING_ALREADY_EXISTS_CODE = "error.kp_booking_already_exists";

export type BookingSummaryServiceLine = { label: string; amount: number };
export type DraftBookingRequirementValue = {
  text?: string;
  file?: File | null;
};
export type DraftBookingService = {
  serviceId: string;
  quantity: number;
  requirements?: Record<string, DraftBookingRequirementValue>;
};

interface KpBookingSummaryStepProps {
  eventId: string;
  isLoadingBooking: boolean;
  isProfileConfirmed: boolean;
  vatRatePercent: number;
  termsUrl: string | null;
  draftZone: BoothZoneWithAvailabilityResponse | null;
  isRegistrationOpen: boolean;
  draftServices?: DraftBookingService[];
  onConfirmStateChange?: (state: BookingConfirmState | null) => void;
}

export type BookingConfirmState = {
  onConfirm: () => Promise<void>;
  disabled: boolean;
  loading: boolean;
};

const KpBookingSummaryStep = ({
  eventId,
  isLoadingBooking,
  isProfileConfirmed,
  vatRatePercent,
  termsUrl,
  draftZone,
  isRegistrationOpen,
  draftServices = [],
  onConfirmStateChange,
}: KpBookingSummaryStepProps) => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [agbAccepted, setAgbAccepted] = useState(false);
  const [bindingAccepted, setBindingAccepted] = useState(false);
  const [consentHighlight, setConsentHighlight] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const agbCheckboxRef = useRef<HTMLInputElement>(null);
  const bindingCheckboxRef = useRef<HTMLInputElement>(null);
  const { data: services } = useListAvailableServices(eventId);
  const serviceById = new Map(
    (services ?? []).map((service) => [service.id, service]),
  );
  const includedQuantities = includedQuantitiesByServiceId(
    draftZone?.included_services ?? [],
  );
  const lineForDraftService = (item: DraftBookingService) => {
    const service = serviceById.get(item.serviceId);
    const name = service?.name ?? item.serviceId;
    const included = includedQuantities.get(item.serviceId) ?? 0;
    const charged = chargedServiceQuantity(item.quantity, included);
    return {
      label: serviceLineLabel(
        name,
        charged,
        included > 0
          ? t("kp.booking.service_included_note", { included })
          : null,
      ),
      amount: (service?.price ?? 0) * charged,
    };
  };
  const linesOfCategory = (category: KpServiceCategory) =>
    draftServices
      .filter((item) => serviceById.get(item.serviceId)?.category === category)
      .map(lineForDraftService);
  const serviceGroups = [
    {
      title: t("kp.booking.summary_group_services"),
      lines: linesOfCategory(KpServiceCategory.SERVICE),
    },
    {
      title: t("kp.booking.summary_group_booth_elements"),
      lines: linesOfCategory(KpServiceCategory.BOOTH_ELEMENT),
    },
  ].filter((group) => group.lines.length > 0);
  const netTotal =
    (draftZone?.base_price ?? 0) +
    serviceGroups.reduce(
      (total, group) =>
        total + group.lines.reduce((sum, line) => sum + line.amount, 0),
      0,
    );

  useEffect(() => {
    setAgbAccepted(false);
    setBindingAccepted(false);
    setConsentHighlight(false);
  }, [draftZone?.id]);

  useEffect(() => {
    if (agbAccepted && bindingAccepted) {
      setConsentHighlight(false);
    }
  }, [agbAccepted, bindingAccepted]);

  const { mutateAsync: register } = useRegisterBooking();
  const { mutateAsync: uploadBookingRequirementFile } =
    useUploadBookingRequirementFile();
  const { mutateAsync: upsertBookingRequirementText } =
    useUpsertBookingRequirementText();

  const saveDraftRequirements = useCallback(
    async (booking: BookingResponse) => {
      for (const draftService of draftServices) {
        const bookingService = booking.services?.find(
          (item) => item.service_id === draftService.serviceId,
        );
        if (!bookingService) continue;
        for (const [requirementId, value] of Object.entries(
          draftService.requirements ?? {},
        )) {
          if (value.text?.trim()) {
            await upsertBookingRequirementText({
              bookingServiceId: bookingService.id,
              requirementId,
              data: { text_value: value.text.trim() },
            });
            continue;
          }
          if (!value.file) continue;
          await uploadBookingRequirementFile({
            bookingServiceId: bookingService.id,
            requirementId,
            data: { file: value.file },
          });
        }
      }
    },
    [draftServices, uploadBookingRequirementFile, upsertBookingRequirementText],
  );

  const navigateToExistingBooking = useCallback(async () => {
    const latestBooking = await getMyBooking(eventId).catch(() => null);
    if (!latestBooking) return;
    queryClient.setQueryData(getGetMyBookingQueryKey(eventId), latestBooking);
    const existingBooking = activeBooking(latestBooking);
    if (!existingBooking) return;
    navigate(`/kp/${eventId}/booking/${existingBooking.id}`);
  }, [eventId, navigate, queryClient]);

  const handleConfirmBooking = useCallback(async () => {
    if (!draftZone || isSubmitting) {
      return;
    }
    if (draftZone.is_full) {
      notifications.show({
        color: "red",
        title: t("error.title"),
        message: t("error.kp_booth_zone_at_capacity"),
      });
      return;
    }
    if (!agbAccepted || !bindingAccepted) {
      setConsentHighlight(true);
      const targetInput = !agbAccepted
        ? agbCheckboxRef.current
        : bindingCheckboxRef.current;
      window.requestAnimationFrame(() => {
        targetInput?.scrollIntoView({ behavior: "smooth", block: "center" });
        targetInput?.focus();
      });
      return;
    }
    const data = {
      booth_zone_id: draftZone.id,
      confirm_profile: isProfileConfirmed,
      services: draftServices.map((service) => ({
        service_id: service.serviceId,
        quantity: service.quantity,
      })),
    } satisfies RegisterBookingRequest & {
      services: { service_id: string; quantity: number }[];
    };

    setIsSubmitting(true);
    try {
      let booking: BookingResponse;
      try {
        booking = await register({ eventId, data });
      } catch (error) {
        if (getApiErrorCode(error) === BOOKING_ALREADY_EXISTS_CODE) {
          await navigateToExistingBooking();
        }
        return;
      }

      let requirementsSaved = true;
      try {
        await saveDraftRequirements(booking);
      } catch {
        requirementsSaved = false;
      }

      void queryClient.invalidateQueries({
        queryKey: getGetMyBookingQueryKey(eventId),
      });
      void queryClient.invalidateQueries({
        queryKey: getListAvailableBoothZonesQueryKey(eventId),
      });

      if (!requirementsSaved) {
        notifications.show({
          color: "yellow",
          title: t("kp.booking.register_requirements_failed_title"),
          message: t("kp.booking.register_requirements_failed_message"),
        });
        navigate(`/kp/${eventId}/booking/${booking.id}/manage/services`);
        return;
      }

      navigate(`/kp/${eventId}/booking/${booking.id}`, {
        state: { fromBookingProcess: true },
      });
    } finally {
      setIsSubmitting(false);
    }
  }, [
    draftZone,
    isSubmitting,
    isProfileConfirmed,
    t,
    register,
    eventId,
    agbAccepted,
    bindingAccepted,
    draftServices,
    navigateToExistingBooking,
    saveDraftRequirements,
    queryClient,
    navigate,
  ]);

  useEffect(() => {
    if (!onConfirmStateChange) return;
    if (!draftZone || !isRegistrationOpen) {
      onConfirmStateChange(null);
      return;
    }
    onConfirmStateChange({
      onConfirm: handleConfirmBooking,
      disabled: isSubmitting,
      loading: isSubmitting,
    });
    return () => onConfirmStateChange(null);
  }, [
    onConfirmStateChange,
    draftZone,
    isRegistrationOpen,
    handleConfirmBooking,
    isSubmitting,
  ]);

  const requiredLabel = (content: ReactNode, showError: boolean) => (
    <Text
      component="span"
      size="sm"
      lh={1.45}
      c={showError ? "red" : undefined}
    >
      {content}
      <Text component="span" c="red" fw={700} ml={4} aria-hidden>
        *
      </Text>
    </Text>
  );

  const agbLabelContent = termsUrl ? (
    <>
      {t("kp.booking.confirm_agb_prefix")}{" "}
      <Anchor href={termsUrl} target="_blank" rel="noopener noreferrer">
        {t("kp.booking.confirm_agb_link")}
      </Anchor>
    </>
  ) : (
    t("kp.booking.confirm_agb_checkbox")
  );

  if (isLoadingBooking) {
    return (
      <Center py="xl">
        <Loader />
      </Center>
    );
  }

  if (!draftZone) {
    return (
      <Card withBorder radius="md" p="lg" mt="xs">
        <Title order={4} mb="md">
          {t("kp.booking.summary_title")}
        </Title>
        <Alert icon={<IconAlertCircle />} color="yellow" mb="md">
          {t("kp.booking.summary_select_zone_first")}
        </Alert>
        <Text c="dimmed" size="sm">
          {t("kp.booking.summary_select_zone_hint")}
        </Text>
      </Card>
    );
  }

  return (
    <Card withBorder radius="md" p="lg" mt="xs">
      <Title order={4} mb="md">
        {t("kp.booking.summary_title")}
      </Title>
      <Stack gap="sm">
        <Group justify="space-between" align="flex-start" wrap="nowrap">
          <Text size="sm" fw={500}>
            {t("kp.booking.summary_zone")}
          </Text>
          <Text size="sm" ta="right">
            {draftZone.name}
          </Text>
        </Group>
        <Group justify="space-between" align="flex-start" wrap="nowrap">
          <Text size="sm" fw={500}>
            {t("kp.booking.summary_booth_nr")}
          </Text>
          <Text size="sm" ta="right">
            {t("kp.booking.booth_nr_pending")}
          </Text>
        </Group>
        <Group justify="space-between" align="flex-start" wrap="nowrap">
          <Text size="sm" fw={500}>
            {t("kp.booking.summary_price")}
          </Text>
          <Text size="sm" ta="right">
            CHF {formatPrice(draftZone.base_price)}
          </Text>
        </Group>
        <SummaryPriceBreakdown
          groups={serviceGroups}
          price={priceBreakdown(netTotal, vatRatePercent)}
          vatRatePercent={vatRatePercent}
        />
      </Stack>
      {!isRegistrationOpen ? (
        <Alert icon={<IconAlertCircle />} color="yellow" mt="md">
          {t("kp.booking.registration_closed")}
        </Alert>
      ) : (
        <>
          <Stack gap="sm" mt="lg">
            <Checkbox
              ref={agbCheckboxRef}
              checked={agbAccepted}
              onChange={(e) => setAgbAccepted(e.currentTarget.checked)}
              label={requiredLabel(
                agbLabelContent,
                consentHighlight && !agbAccepted,
              )}
            />
            <Checkbox
              ref={bindingCheckboxRef}
              checked={bindingAccepted}
              onChange={(e) => setBindingAccepted(e.currentTarget.checked)}
              label={requiredLabel(
                t("kp.booking.confirm_binding_checkbox"),
                consentHighlight && !bindingAccepted,
              )}
            />
          </Stack>
        </>
      )}
    </Card>
  );
};
export default KpBookingSummaryStep;
