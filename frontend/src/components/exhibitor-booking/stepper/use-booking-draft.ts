import { useCallback, useEffect, useMemo, useState } from "react";
import type {
  BoothZoneWithAvailabilityResponse,
  IncludedServiceResponse,
  ServiceResponse,
} from "../../../orval/generated/fastAPI.schemas";
import {
  clampServiceQuantity,
  excludedByService,
  includedQuantitiesByServiceId,
  withPackageInclusions,
} from "../../../utils/kp-service-quantity";
import type { DraftBookingService } from "../KpBookingSummaryStep";

const NO_INCLUDED_SERVICES: IncludedServiceResponse[] = [];

const seededDraft = (
  draftServices: DraftBookingService[],
  allServices: ServiceResponse[],
  includedQuantities: Map<string, number>,
) => {
  const clamped = draftServices.map((selected) => {
    const service = allServices.find((item) => item.id === selected.serviceId);
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
  return isUnchanged ? draftServices : [...clamped, ...seeded];
};

export const useBookingDraft = (allServices: ServiceResponse[]) => {
  const [selectedZone, setSelectedZone] =
    useState<BoothZoneWithAvailabilityResponse | null>(null);
  const [draftServices, setDraftServices] = useState<DraftBookingService[]>([]);

  const zoneIncludedQuantities = useMemo(
    () =>
      includedQuantitiesByServiceId(
        selectedZone?.included_services ?? NO_INCLUDED_SERVICES,
      ),
    [selectedZone],
  );
  const includedQuantities = useMemo(
    () =>
      withPackageInclusions(zoneIncludedQuantities, allServices, draftServices),
    [zoneIncludedQuantities, allServices, draftServices],
  );
  const excludedBy = useMemo(
    () => excludedByService(allServices, draftServices, zoneIncludedQuantities),
    [allServices, draftServices, zoneIncludedQuantities],
  );

  const selectZone = useCallback(
    (zone: BoothZoneWithAvailabilityResponse | null) => {
      if (zone?.id !== selectedZone?.id) setDraftServices([]);
      setSelectedZone(zone);
    },
    [selectedZone?.id],
  );

  useEffect(() => {
    if (allServices.length === 0) return;
    const next = seededDraft(draftServices, allServices, includedQuantities);
    if (next !== draftServices) setDraftServices(next);
  }, [allServices, includedQuantities, draftServices]);

  return {
    selectedZone,
    selectZone,
    draftServices,
    setDraftServices,
    includedQuantities,
    excludedBy,
  };
};
