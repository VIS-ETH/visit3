import { Button, Group, Modal, Stack, Text } from "@mantine/core";
import { IconPlus } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import type { ServiceResponse } from "../../../orval/generated/fastAPI.schemas";
import { formatMoney } from "../../../utils/money";
import { priceBreakdown } from "../../../utils/pricing";

export type SelectedService = {
  service: ServiceResponse;
  quantity: number;
};

const PriceRow = ({
  label,
  value,
  strong = false,
}: {
  label: string;
  value: number;
  strong?: boolean;
}) => (
  <Group justify="space-between">
    <Text size={strong ? undefined : "sm"} fw={strong ? 600 : undefined}>
      {label}
    </Text>
    <Text size={strong ? undefined : "sm"} fw={strong ? 700 : undefined}>
      {formatMoney(value)}
    </Text>
  </Group>
);

const AddServicesConfirmModal = ({
  isSubmitting,
  onClose,
  onSubmit,
  opened,
  selectedServices,
  vatRatePercent,
}: {
  isSubmitting: boolean;
  onClose: () => void;
  onSubmit: () => void;
  opened: boolean;
  selectedServices: SelectedService[];
  vatRatePercent: number;
}) => {
  const { t } = useTranslation();
  const net = selectedServices.reduce(
    (sum, item) => sum + item.service.price * item.quantity,
    0,
  );
  const price = priceBreakdown(net, vatRatePercent);

  return (
    <Modal
      centered
      opened={opened}
      onClose={onClose}
      title={t("kp.booking_manage.confirm_add_services_title")}
    >
      <Stack gap="md">
        <Text size="sm">
          {t("kp.booking_manage.confirm_add_services_body")}
        </Text>
        <Stack gap="xs">
          {selectedServices.map((item) => (
            <Group justify="space-between" key={item.service.id}>
              <Text size="sm">
                {item.service.name} × {item.quantity}
              </Text>
              <Text size="sm" fw={600}>
                {formatMoney(item.service.price * item.quantity)}
              </Text>
            </Group>
          ))}
        </Stack>
        <PriceRow label={t("kp.booking.summary_net")} value={price.net} />
        <PriceRow
          label={t("kp.booking.summary_vat_rate", { rate: vatRatePercent })}
          value={price.vat}
        />
        <PriceRow
          label={t("kp.booking.summary_gross")}
          value={price.gross}
          strong
        />
        <Group justify="flex-end">
          <Button variant="subtle" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button
            leftSection={<IconPlus size={16} />}
            loading={isSubmitting}
            onClick={onSubmit}
          >
            {t("kp.booking_manage.confirm_add_services_submit")}
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
};

export default AddServicesConfirmModal;
