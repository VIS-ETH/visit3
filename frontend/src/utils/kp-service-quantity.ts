import type {
  IncludedServiceResponse,
  KpServiceCategory,
  ServiceResponse,
} from "../orval/generated/fastAPI.schemas";

export function servicesOfCategory(
  services: ServiceResponse[],
  category: KpServiceCategory,
) {
  return services.filter((service) => service.category === category);
}

export function includedQuantitiesByServiceId(
  includedServices: IncludedServiceResponse[],
): Map<string, number> {
  return new Map(
    includedServices.map((included) => [
      included.service_id,
      included.included_quantity,
    ]),
  );
}

export function maxServiceQuantity(service: ServiceResponse, included: number) {
  const remaining = service.remaining_total_quantity;
  return remaining == null
    ? service.max_quantity_per_booking
    : Math.min(service.max_quantity_per_booking, included + remaining);
}

export function clampServiceQuantity(
  service: ServiceResponse,
  included: number,
  quantity: number,
) {
  return Math.max(
    Math.min(Math.trunc(quantity), maxServiceQuantity(service, included)),
    included,
  );
}

export function chargedServiceQuantity(quantity: number, included: number) {
  return Math.max(quantity - included, 0);
}

export function serviceLineLabel(
  name: string,
  chargedQuantity: number,
  includedNote: string | null,
) {
  const label = chargedQuantity > 1 ? `${name} × ${chargedQuantity}` : name;
  return includedNote ? `${label} (${includedNote})` : label;
}

type SelectedQuantity = { serviceId: string; quantity: number };

export function withPackageInclusions(
  zoneIncluded: Map<string, number>,
  services: ServiceResponse[],
  selected: SelectedQuantity[],
): Map<string, number> {
  const included = new Map(zoneIncluded);
  const serviceById = new Map(services.map((service) => [service.id, service]));
  for (const item of selected) {
    if (item.quantity <= 0) continue;
    for (const content of serviceById.get(item.serviceId)?.included_services ??
      []) {
      included.set(
        content.service_id,
        (included.get(content.service_id) ?? 0) + content.included_quantity,
      );
    }
  }
  return included;
}

export function excludedByService(
  services: ServiceResponse[],
  selected: SelectedQuantity[],
  zoneIncluded: Map<string, number>,
): Map<string, string> {
  const serviceById = new Map(services.map((service) => [service.id, service]));
  const excludedBy = new Map<string, string>();
  for (const item of selected) {
    if (item.quantity <= (zoneIncluded.get(item.serviceId) ?? 0)) continue;
    const service = serviceById.get(item.serviceId);
    if (!service) continue;
    for (const excludedId of service.excluded_service_ids ?? []) {
      if (!excludedBy.has(excludedId)) excludedBy.set(excludedId, service.name);
    }
  }
  return excludedBy;
}

export function blockingServiceName(
  service: ServiceResponse,
  excludedBy: Map<string, string>,
): string | null {
  const own = excludedBy.get(service.id);
  if (own) return own;
  for (const content of service.included_services ?? []) {
    const blocking = excludedBy.get(content.service_id);
    if (blocking) return blocking;
  }
  return null;
}
