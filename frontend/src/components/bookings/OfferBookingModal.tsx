import {
  Alert,
  Button,
  Group,
  Modal,
  Select,
  Stack,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconAlertCircle } from "@tabler/icons-react";
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
  const { mutateAsync: offer, isPending } = useOfferBooking();
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
    notifications.show({
      color: "green",
      message: t("kp.manage.offer_success"),
    });
    close();
  };

  return (
    <Modal
      opened={opened}
      onClose={close}
      title={t("kp.manage.offer_button")}
      centered
    >
      <Stack gap="sm">
        {errorCode ? (
          <Alert color="red" icon={<IconAlertCircle />}>
            {t(errorCode)}
          </Alert>
        ) : null}
        <Select
          label={t("kp.manage.booking_company")}
          data={(companies ?? []).map((company) => ({
            value: company.id,
            label: company.name,
          }))}
          value={companyId}
          onChange={setCompanyId}
          searchable
          disabled={isPending}
        />
        <Select
          label={t("kp.manage.booking_booth_zone")}
          data={(zones ?? []).map((zone) => ({
            value: zone.id,
            label: zone.name,
          }))}
          value={zoneId}
          onChange={setZoneId}
          disabled={isPending}
        />
        <TextInput
          label={t("kp.manage.offer_deadline")}
          placeholder={t("kp.dashboard.date_input_placeholder")}
          value={deadline}
          onChange={(event) => setDeadline(event.currentTarget.value)}
          disabled={isPending}
        />
        <Group justify="flex-end">
          <Button variant="default" onClick={close} disabled={isPending}>
            {t("common.cancel")}
          </Button>
          <Button
            loading={isPending}
            disabled={!isValid}
            onClick={() => void submit()}
          >
            {t("kp.manage.offer_button")}
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
};

export default OfferBookingModal;
