import {
  Badge,
  Group,
  NumberInput,
  Paper,
  Stack,
  Switch,
  Text,
} from "@mantine/core";
import { useTranslation } from "react-i18next";
import type { ServiceResponse } from "../../../orval/generated/fastAPI.schemas";
import { maxServiceQuantity } from "../../../utils/kp-service-quantity";
import { formatMoney } from "../../../utils/money";

const AddServiceCard = ({
  blockedBy,
  bookedQuantity,
  contents,
  editable,
  includedQuantity,
  onQuantityChange,
  quantity,
  service,
}: {
  blockedBy: string | null;
  bookedQuantity: number;
  contents: string;
  editable: boolean;
  includedQuantity: number;
  onQuantityChange: (quantity: number) => void;
  quantity: number;
  service: ServiceResponse;
}) => {
  const { t } = useTranslation();
  const maxQuantity = maxServiceQuantity(service, bookedQuantity);
  const addedQuantity = Math.max(quantity - bookedQuantity, 0);
  const isBlocked = blockedBy !== null && quantity <= bookedQuantity;

  return (
    <Paper withBorder radius="sm" p="md">
      <Stack gap="xs">
        <Group justify="space-between" align="flex-start">
          <div>
            <Text fw={600}>{service.name}</Text>
            {service.description ? (
              <Text c="dimmed" size="sm">
                {service.description}
              </Text>
            ) : null}
            {contents ? (
              <Text c="dimmed" size="xs">
                {t("kp.booking.service_contains", { contents })}
              </Text>
            ) : null}
          </div>
          <Stack gap={4} align="flex-end">
            <Text fw={600} size="sm">
              {formatMoney(service.price)}
            </Text>
            {includedQuantity > 0 ? (
              <Badge color="green" variant="light">
                {t("kp.booking.service_included_note", {
                  included: includedQuantity,
                })}
              </Badge>
            ) : null}
          </Stack>
        </Group>
        {service.max_quantity_per_booking === 1 ? (
          <Switch
            checked={quantity > 0}
            disabled={!editable || isBlocked || maxQuantity <= bookedQuantity}
            label={t("kp.booking.service_book_toggle")}
            onChange={(event) =>
              onQuantityChange(event.currentTarget.checked ? 1 : 0)
            }
          />
        ) : (
          <NumberInput
            allowDecimal={false}
            allowNegative={false}
            clampBehavior="strict"
            disabled={!editable || isBlocked || maxQuantity <= bookedQuantity}
            label={
              service.unit_label
                ? t("kp.booking.service_quantity_with_unit", {
                    unit: service.unit_label,
                  })
                : t("kp.booking.service_quantity")
            }
            min={bookedQuantity}
            max={maxQuantity}
            step={1}
            value={quantity}
            onChange={(value) =>
              onQuantityChange(
                typeof value === "number" ? value : Number(value) || 0,
              )
            }
          />
        )}
        {blockedBy !== null ? (
          <Text c="orange" size="xs">
            {t("kp.booking.service_excluded_by", { name: blockedBy })}
          </Text>
        ) : null}
        {service.remaining_total_quantity != null ? (
          <Text c="dimmed" size="xs">
            {t("kp.booking.service_remaining_total", {
              remaining: service.remaining_total_quantity,
            })}
          </Text>
        ) : null}
        {addedQuantity > 0 ? (
          <Group justify="space-between" wrap="nowrap">
            <Text size="sm" c="dimmed">
              {t("kp.booking.service_line_total")}
            </Text>
            <Text fw={600} size="sm">
              {formatMoney(service.price * addedQuantity)}
            </Text>
          </Group>
        ) : null}
      </Stack>
    </Paper>
  );
};

export default AddServiceCard;
