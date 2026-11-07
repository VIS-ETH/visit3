import { Select, TextInput } from "@mantine/core";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { getApiErrorCode } from "../../api/errors";
import { useListCompanies } from "../../orval/generated/company/company";
import {
  getListEventBookingsQueryKey,
  useListBoothZones,
  useOfferBooking,
} from "../../orval/generated/kp/kp";
import { parseKpDateInput, toKpIsoDate } from "../../utils/kp-utils";
import { notifySuccess } from "../../utils/notify";
import ErrorAlert from "../ErrorAlert";
import BookingActionModal from "./BookingActionModal";

const REFUSED_OFFER_STATUSES = [400, 404, 409, 422];

const OfferBookingModal = ({
  eventId,
  opened,
  onClose,
}: {
  eventId: string;
  opened: boolean;
  onClose: () => void;
}) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data: companies } = useListCompanies({ query: { enabled: opened } });
  const { data: zones } = useListBoothZones(eventId, {
    query: { enabled: opened },
  });
  const [companyId, setCompanyId] = useState<string | null>(null);
  const [zoneId, setZoneId] = useState<string | null>(null);
  const [deadline, setDeadline] = useState("");
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const { mutateAsync: offer } = useOfferBooking({
    request: { quietStatuses: REFUSED_OFFER_STATUSES },
  });
  const isValid =
    companyId !== null &&
    zoneId !== null &&
    parseKpDateInput(deadline) !== null;

  const close = () => {
    setCompanyId(null);
    setZoneId(null);
    setDeadline("");
    setErrorCode(null);
    onClose();
  };

  const submit = async () => {
    if (companyId === null || zoneId === null) return;
    setErrorCode(null);
    try {
      await offer({
        eventId,
        data: {
          company_id: companyId,
          booth_zone_id: zoneId,
          deadline: toKpIsoDate(deadline),
        },
      });
    } catch (error) {
      setErrorCode(getApiErrorCode(error) ?? "error.internal");
      return;
    }
    await queryClient.invalidateQueries({
      queryKey: getListEventBookingsQueryKey(eventId),
    });
    notifySuccess(t("kp.manage.offer_success"));
    close();
  };

  return (
    <BookingActionModal
      isSubmitDisabled={!isValid}
      onClose={close}
      onSubmit={submit}
      opened={opened}
      submitLabel={t("kp.manage.offer_button")}
      title={t("kp.manage.offer_button")}
    >
      {(isSubmitting) => (
        <>
          {errorCode ? <ErrorAlert>{t(errorCode)}</ErrorAlert> : null}
          <Select
            label={t("kp.manage.booking_company")}
            data={(companies ?? []).map((company) => ({
              value: company.id,
              label: company.name,
            }))}
            value={companyId}
            onChange={setCompanyId}
            searchable
            disabled={isSubmitting}
          />
          <Select
            label={t("kp.manage.booking_booth_zone")}
            data={(zones ?? []).map((zone) => ({
              value: zone.id,
              label: zone.name,
            }))}
            value={zoneId}
            onChange={setZoneId}
            disabled={isSubmitting}
          />
          <TextInput
            label={t("kp.manage.offer_deadline")}
            placeholder={t("kp.dashboard.date_input_placeholder")}
            value={deadline}
            onChange={(event) => setDeadline(event.currentTarget.value)}
            disabled={isSubmitting}
          />
        </>
      )}
    </BookingActionModal>
  );
};

export default OfferBookingModal;
