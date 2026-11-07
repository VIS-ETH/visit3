import type { z } from "zod";
import {
  KpServiceCategory,
  type KpEventServiceRequirementType,
  type ServiceResponse,
} from "../../orval/generated/fastAPI.schemas";
import type { serviceSchema } from "../../schemas/kpSchema";
import {
  centsToCurrencyAmount,
  currencyAmountToCents,
} from "../../utils/price-utils";

export type ServiceFormValues = z.infer<typeof serviceSchema>;

export const emptyServiceFormValues: ServiceFormValues = {
  name: "",
  description: "",
  category: KpServiceCategory.SERVICE,
  unitLabel: "",
  imageUrl: "",
  price: 0,
  maxPerBooking: 1,
  maxTotal: 0,
  isActive: true,
  requirements: [],
  includedServices: [],
  excludedServiceIds: [],
};

export const toServiceFormValues = (
  service: ServiceResponse,
): ServiceFormValues => ({
  name: service.name,
  description: service.description,
  category: service.category,
  unitLabel: service.unit_label ?? "",
  imageUrl: service.image_url ?? "",
  price: centsToCurrencyAmount(service.price),
  maxPerBooking: service.max_quantity_per_booking,
  maxTotal: service.max_total_quantity,
  isActive: service.is_active,
  requirements: service.requirements.map((requirement) => ({
    id: requirement.id,
    type: requirement.type,
    name: requirement.name,
    description: requirement.description,
    order: requirement.order,
  })),
  includedServices: (service.included_services ?? []).map((included) => ({
    serviceId: included.service_id,
    quantity: included.included_quantity,
  })),
  excludedServiceIds: service.excluded_service_ids ?? [],
});

export const toServiceRequest = (values: ServiceFormValues) => ({
  name: values.name.trim(),
  description: values.description,
  category: values.category as KpServiceCategory,
  unit_label: values.unitLabel.trim() || null,
  price: currencyAmountToCents(values.price),
  max_quantity_per_booking: values.maxPerBooking,
  max_total_quantity: values.maxTotal,
  is_active: values.isActive,
  requirements: values.requirements.map((requirement) => ({
    ...requirement,
    type: requirement.type as KpEventServiceRequirementType,
  })),
  included_services: values.includedServices.map((included) => ({
    service_id: included.serviceId,
    included_quantity: included.quantity,
  })),
  excluded_service_ids: values.excludedServiceIds,
});
