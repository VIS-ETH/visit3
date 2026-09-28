import type { BoothZoneWithAvailabilityResponse } from "../orval/generated/fastAPI.schemas";

export const isZoneBookable = (zone: BoothZoneWithAvailabilityResponse) =>
  zone.registration_open && !zone.is_full;
