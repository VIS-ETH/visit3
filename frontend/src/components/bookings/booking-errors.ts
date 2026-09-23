import { getApiErrorCode } from "../../api/errors";

export type BookingEditFieldErrors = {
  boothNr?: string;
  services?: string;
  zone?: string;
};

const ZONE_ERROR_CODES = [
  "error.kp_booth_zone_full",
  "error.kp_booth_zone_at_capacity",
  "error.kp_booth_zone_not_found",
  "error.kp_booth_zone_event_mismatch",
];

const BOOTH_NUMBER_ERROR_CODE = "error.kp_booth_number_taken";
const SERVICE_QUANTITY_ERROR_CODE = "error.kp_service_quantity_invalid";

export const bookingEditFieldErrors = (
  error: unknown,
): BookingEditFieldErrors => {
  const code = getApiErrorCode(error);
  if (!code) return {};
  if (ZONE_ERROR_CODES.includes(code)) return { zone: code };
  if (code === BOOTH_NUMBER_ERROR_CODE) return { boothNr: code };
  if (code === SERVICE_QUANTITY_ERROR_CODE) return { services: code };
  return {};
};
