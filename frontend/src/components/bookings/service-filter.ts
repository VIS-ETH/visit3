import {
  KpServiceCategory,
  type ServiceResponse,
} from "../../orval/generated/fastAPI.schemas";

export type FilterService = Pick<
  ServiceResponse,
  "id" | "name" | "category" | "order"
>;

interface BookedService {
  service_id: string;
  service: Pick<ServiceResponse, "category">;
}

export const SERVICE_CATEGORY_LABEL_KEYS: Record<
  KpServiceCategory,
  { group: string; any: string }
> = {
  SERVICE: {
    group: "kp.manage.services_group_services",
    any: "kp.manage.service_filter_any_service",
  },
  BOOTH_ELEMENT: {
    group: "kp.manage.services_group_booth_elements",
    any: "kp.manage.service_filter_any_booth_element",
  },
};

export const isServiceCategory = (value: string): value is KpServiceCategory =>
  Object.values(KpServiceCategory).some((category) => category === value);

export function servicesByCategory(services: FilterService[]) {
  const unique = [
    ...new Map(services.map((service) => [service.id, service])).values(),
  ].sort(
    (left, right) =>
      left.order - right.order || left.name.localeCompare(right.name),
  );
  return Object.values(KpServiceCategory)
    .map((category) => ({
      category,
      services: unique.filter((service) => service.category === category),
    }))
    .filter((group) => group.services.length > 0);
}

export function bookedAnyService(
  booked: BookedService[],
  selected: string[],
): boolean {
  return (
    selected.length === 0 ||
    booked.some(
      (entry) =>
        selected.includes(entry.service_id) ||
        selected.includes(entry.service.category),
    )
  );
}
