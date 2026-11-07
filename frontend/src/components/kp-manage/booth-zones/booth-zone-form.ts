import type { z } from "zod";
import type { StaffBoothZoneResponse } from "../../../orval/generated/fastAPI.schemas";
import type { boothZoneSchema } from "../../../schemas/kpSchema";
import {
  centsToCurrencyAmount,
  currencyAmountToCents,
} from "../../../utils/price-utils";

export type BoothZoneFormValues = z.infer<typeof boothZoneSchema>;

export const emptyZoneValues: BoothZoneFormValues = {
  name: "",
  description: "",
  color: "#000000",
  capacity: 0,
  boothSize: 0,
  basePrice: 0,
  layoutDescription: "",
  includedServices: [],
};

export const toZoneFormValues = (
  zone: StaffBoothZoneResponse,
): BoothZoneFormValues => ({
  name: zone.name,
  description: zone.description,
  color: zone.color,
  capacity: zone.capacity,
  boothSize: zone.booth_size,
  basePrice: centsToCurrencyAmount(zone.base_price),
  layoutDescription: zone.layout_description ?? "",
  includedServices: zone.included_services.map((included) => ({
    serviceId: included.service_id,
    quantity: included.included_quantity,
  })),
});

export const toZoneRequest = (values: BoothZoneFormValues) => ({
  name: values.name.trim(),
  description: values.description,
  color: values.color,
  capacity: values.capacity,
  booth_size: values.boothSize,
  base_price: currencyAmountToCents(values.basePrice),
  layout_description: values.layoutDescription.trim() || null,
  included_services: values.includedServices.map((included) => ({
    service_id: included.serviceId,
    included_quantity: included.quantity,
  })),
});
