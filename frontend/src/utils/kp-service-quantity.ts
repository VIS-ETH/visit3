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
