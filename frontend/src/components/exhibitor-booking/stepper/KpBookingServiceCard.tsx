import {
  Badge,
  Group,
  Image,
  NumberInput,
  Paper,
  Stack,
  Switch,
  Text,
  ThemeIcon,
  Tooltip,
} from "@mantine/core";
import { IconInfoCircle } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import type { ServiceResponse } from "../../../orval/generated/fastAPI.schemas";
import {
  chargedServiceQuantity,
  maxServiceQuantity,
} from "../../../utils/kp-service-quantity";
import { formatMoney } from "../../../utils/money";
import type {
  DraftBookingRequirementValue,
  DraftBookingService,
} from "../KpBookingSummaryStep";
import ServiceRequirementField from "./ServiceRequirementField";

interface KpBookingServiceCardProps {
  service: ServiceResponse;
  selectedService: DraftBookingService | undefined;
  included: number;
  blockedBy: string | null;
  contents: string;
  showVatHint: boolean;
  onQuantityChange: (quantity: number) => void;
  onRequirementChange: (
    requirementId: string,
    value: DraftBookingRequirementValue,
  ) => void;
}

const KpBookingServiceCard = ({
  service,
  selectedService,
  included,
  blockedBy,
  contents,
  showVatHint,
  onQuantityChange,
  onRequirementChange,
}: KpBookingServiceCardProps) => {
  const { t } = useTranslation();
  const quantity = selectedService?.quantity ?? included;
  const charged = chargedServiceQuantity(quantity, included);
  const isBlocked = blockedBy !== null && quantity <= included;

  return (
    <Paper withBorder radius="md" p="md">
      <Stack gap="xs">
        {service.image_url ? (
          <Image
            alt={service.name}
            fit="cover"
            h={96}
            radius="sm"
            src={service.image_url}
          />
        ) : null}
        <Group justify="space-between" align="flex-start" wrap="nowrap">
          <div style={{ minWidth: 0 }}>
            <Text fw={600}>{service.name}</Text>
            {service.description ? (
              <Text c="dimmed" size="sm" mt={4}>
                {service.description}
              </Text>
            ) : null}
            {contents ? (
              <Text c="dimmed" size="xs" mt={4}>
                {t("kp.booking.service_contains", { contents })}
              </Text>
            ) : null}
          </div>
          <Stack gap={4} align="flex-end">
            <Group gap={6} wrap="nowrap">
              <Text fw={600} size="sm" ta="right">
                {formatMoney(service.price)}
              </Text>
              {showVatHint ? (
                <Tooltip
                  multiline
                  w={240}
                  label={t("kp.booking.price_excl_vat_hint")}
                >
                  <ThemeIcon
                    aria-label={t("kp.booking.price_excl_vat_hint")}
                    color="gray"
                    size="sm"
                    variant="subtle"
                  >
                    <IconInfoCircle size={16} />
                  </ThemeIcon>
                </Tooltip>
              ) : null}
            </Group>
            {included > 0 ? (
              <Badge color="green" variant="light">
                {t("kp.booking.service_included_note", { included })}
              </Badge>
            ) : null}
          </Stack>
        </Group>
        {service.max_quantity_per_booking === 1 ? (
          <Switch
            checked={quantity > 0}
            disabled={
              isBlocked || maxServiceQuantity(service, included) <= included
            }
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
            description={t("kp.booking.service_max_per_booking", {
              max: service.max_quantity_per_booking,
            })}
            label={
              service.unit_label
                ? t("kp.booking.service_quantity_with_unit", {
                    unit: service.unit_label,
                  })
                : t("kp.booking.service_quantity")
            }
            disabled={isBlocked}
            min={included}
            max={maxServiceQuantity(service, included)}
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
        {quantity > 0 ? (
          <Group justify="space-between" wrap="nowrap">
            <Text size="sm" c="dimmed">
              {t("kp.booking.service_line_total")}
            </Text>
            <Text fw={600} size="sm">
              {formatMoney(service.price * charged)}
            </Text>
          </Group>
        ) : null}
        {quantity > 0 && service.requirements.length > 0 ? (
          <Stack gap="sm" mt="xs">
            <div>
              <Text size="sm" fw={600}>
                {t("kp.booking.service_requirements")}
              </Text>
              <Text size="xs" c="dimmed">
                {t("kp.booking.service_requirements_later")}
              </Text>
            </div>
            {service.requirements
              .slice()
              .sort((a, b) => a.order - b.order)
              .map((requirement) => (
                <ServiceRequirementField
                  key={requirement.id}
                  requirement={requirement}
                  value={selectedService?.requirements?.[requirement.id]}
                  onChange={(value) =>
                    onRequirementChange(requirement.id, value)
                  }
                />
              ))}
          </Stack>
        ) : null}
      </Stack>
    </Paper>
  );
};

export default KpBookingServiceCard;
