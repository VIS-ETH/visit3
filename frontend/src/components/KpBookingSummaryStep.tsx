import {
  Alert,
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
import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";
import { useListAvailableServices } from "../api/kp-services";
import type {
  BoothZoneWithAvailabilityResponse,
  RegisterBookingRequest,
} from "../orval/generated/fastAPI.schemas";
import {
  getGetMyBookingQueryKey,
  getListAvailableBoothZonesQueryKey,
  useRegisterBooking,
  useUpsertBookingRequirementText,
  useUploadBookingRequirementFile,
} from "../orval/generated/kp/kp";
import { formatPrice } from "../utils/price-utils";
import SummaryPriceBreakdown from "./SummaryPriceBreakdown";

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
  draftZone: BoothZoneWithAvailabilityResponse | null;
  isRegistrationOpen: boolean;
  draftAdditionalServiceLines?: BookingSummaryServiceLine[];
  draftServices?: DraftBookingService[];
  onConfirmStateChange?: (
    state: {
      onConfirm: () => void;
      disabled: boolean;
      loading: boolean;
    } | null,
  ) => void;
}

const KpBookingSummaryStep = ({
  eventId,
  isLoadingBooking,
  draftZone,
  isRegistrationOpen,
  draftAdditionalServiceLines = [],
  draftServices = [],
  onConfirmStateChange,
}: KpBookingSummaryStepProps) => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [agbAccepted, setAgbAccepted] = useState(false);
  const [bindingAccepted, setBindingAccepted] = useState(false);
  const [consentHighlight, setConsentHighlight] = useState(false);
  const agbCheckboxRef = useRef<HTMLInputElement>(null);
  const bindingCheckboxRef = useRef<HTMLInputElement>(null);
  const { data: services } = useListAvailableServices(eventId);
  const serviceById = new Map(
    (services ?? []).map((service) => [service.id, service]),
  );
  const selectedServiceLines = draftServices.map((item) => {
    const service = serviceById.get(item.serviceId);
    return {
      label: service?.name ?? item.serviceId,
      amount: (service?.price ?? 0) * item.quantity,
    };
  });
  const additionalLines =
    draftAdditionalServiceLines.length > 0
      ? draftAdditionalServiceLines
      : selectedServiceLines;

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

  const { mutateAsync: register, isPending: isRegistering } =
    useRegisterBooking();
  const {
    mutateAsync: uploadBookingRequirementFile,
    isPending: isUploadingRequirements,
  } = useUploadBookingRequirementFile();
  const {
    mutateAsync: upsertBookingRequirementText,
    isPending: isSavingRequirementText,
  } = useUpsertBookingRequirementText();

  const handleConfirmBookingClick = useCallback(async () => {
    if (
      !draftZone ||
      isRegistering ||
      isUploadingRequirements ||
      isSavingRequirementText
    ) {
      return;
    }
    if (draftZone.available_spots <= 0) {
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
      services: draftServices.map((service) => ({
        service_id: service.serviceId,
        quantity: service.quantity,
      })),
    } satisfies RegisterBookingRequest & {
      services: { service_id: string; quantity: number }[];
    };
    const booking = await register({ eventId, data });
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
    queryClient.invalidateQueries({
      queryKey: getGetMyBookingQueryKey(eventId),
    });
    queryClient.invalidateQueries({
      queryKey: getListAvailableBoothZonesQueryKey(eventId),
    });
    navigate(`/kp/${eventId}/booking/${booking.id}`, {
      state: { fromBookingProcess: true },
    });
  }, [
    draftZone,
    isRegistering,
    isUploadingRequirements,
    isSavingRequirementText,
    t,
    register,
    eventId,
    agbAccepted,
    bindingAccepted,
    draftServices,
    uploadBookingRequirementFile,
    upsertBookingRequirementText,
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
      onConfirm: handleConfirmBookingClick,
      disabled: isRegistering || isUploadingRequirements || isSavingRequirementText,
      loading: isRegistering || isUploadingRequirements || isSavingRequirementText,
    });
    return () => onConfirmStateChange(null);
  }, [
    onConfirmStateChange,
    draftZone,
    isRegistrationOpen,
    handleConfirmBookingClick,
    isRegistering,
    isUploadingRequirements,
    isSavingRequirementText,
  ]);

  const requiredLabel = (i18nKey: string, showError: boolean) => (
    <Text
      component="span"
      size="sm"
      lh={1.45}
      c={showError ? "red" : undefined}
    >
      {t(i18nKey)}
      <Text component="span" c="red" fw={700} ml={4} aria-hidden>
        *
      </Text>
    </Text>
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
          basePrice={draftZone.base_price}
          additionalLines={additionalLines}
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
                "kp.booking.confirm_agb_checkbox",
                consentHighlight && !agbAccepted,
              )}
            />
            <Checkbox
              ref={bindingCheckboxRef}
              checked={bindingAccepted}
              onChange={(e) => setBindingAccepted(e.currentTarget.checked)}
              label={requiredLabel(
                "kp.booking.confirm_binding_checkbox",
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
