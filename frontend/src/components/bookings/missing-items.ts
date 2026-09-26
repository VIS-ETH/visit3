import { useTranslation } from "react-i18next";
import type { BookingServiceResponse } from "../../orval/generated/fastAPI.schemas";

const REQUIREMENT_ITEM_PREFIX = "requirement:";
const COMPANY_PROFILE_ITEM = "company_profile";
const COMPANY_DESCRIPTION_ITEM = "company_description";
const BILLING_ADDRESS_ITEM = "billing_address";

const requirementLabelsById = (services: BookingServiceResponse[]) =>
  new Map(
    services.flatMap((bookingService) =>
      bookingService.service.requirements.map(
        (requirement) =>
          [
            requirement.id,
            `${bookingService.service.name} · ${requirement.name}`,
          ] as const,
      ),
    ),
  );

export const useMissingItemLabel = (services: BookingServiceResponse[]) => {
  const { t } = useTranslation();
  const requirementLabels = requirementLabelsById(services);

  return (item: string) => {
    if (item.startsWith(REQUIREMENT_ITEM_PREFIX)) {
      return (
        requirementLabels.get(item.slice(REQUIREMENT_ITEM_PREFIX.length)) ??
        t("kp.manage.booking_missing_item_requirement")
      );
    }
    if (item === COMPANY_PROFILE_ITEM) {
      return t("kp.manage.booking_missing_item_company_profile");
    }
    if (item === COMPANY_DESCRIPTION_ITEM) {
      return t("kp.manage.booking_missing_item_company_description");
    }
    if (item === BILLING_ADDRESS_ITEM) {
      return t("kp.manage.booking_missing_item_billing_address");
    }
    return t("kp.manage.booking_missing_item_unknown");
  };
};
