import { formatDateTime } from "../../utils/date-format";

export const formatBookingTimestamp = (value?: string | null) =>
  formatDateTime(value) ?? undefined;
