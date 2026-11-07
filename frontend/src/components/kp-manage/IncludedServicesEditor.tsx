import {
  ActionIcon,
  Button,
  Group,
  NumberInput,
  Select,
  Stack,
  Text,
} from "@mantine/core";
import type { UseFormReturnType } from "@mantine/form";
import { IconPlus, IconTrash } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import type { ServiceResponse } from "../../orval/generated/fastAPI.schemas";

export type IncludedServiceValue = { serviceId: string; quantity: number };

type IncludedServicesValues = { includedServices: IncludedServiceValue[] };

const emptyIncludedService: IncludedServiceValue = {
  serviceId: "",
  quantity: 1,
};

const IncludedServicesEditor = <Values extends IncludedServicesValues>({
  form,
  services,
  excludedServiceIds = [],
  disabled,
  addLabel,
  removeLabel,
  emptyLabel,
}: {
  form: UseFormReturnType<Values>;
  services: ServiceResponse[];
  excludedServiceIds?: string[];
  disabled: boolean;
  addLabel: string;
  removeLabel: string;
  emptyLabel?: string;
}) => {
  const { t } = useTranslation();
  const included = form.values.includedServices;
  const serviceById = new Map(services.map((service) => [service.id, service]));

  const optionsForRow = (index: number) => {
    const takenIds = new Set(
      included
        .filter((_, position) => position !== index)
        .map((entry) => entry.serviceId),
    );
    return services
      .filter(
        (service) =>
          !takenIds.has(service.id) && !excludedServiceIds.includes(service.id),
      )
      .map((service) => ({ value: service.id, label: service.name }));
  };

  return (
    <Stack gap="sm">
      {included.length === 0 && emptyLabel ? (
        <Text c="dimmed" size="sm">
          {emptyLabel}
        </Text>
      ) : null}
      {included.map((entry, index) => (
        <Group align="flex-end" gap="xs" key={index} wrap="nowrap">
          <Select
            data={optionsForRow(index)}
            disabled={disabled}
            flex={1}
            label={t("kp.manage.zone_included_service")}
            searchable
            {...form.getInputProps(`includedServices.${index}.serviceId`)}
          />
          <NumberInput
            allowDecimal={false}
            clampBehavior="strict"
            disabled={disabled}
            label={t("kp.manage.zone_included_quantity")}
            min={1}
            max={
              serviceById.get(entry.serviceId)?.max_quantity_per_booking ?? 999
            }
            w={140}
            {...form.getInputProps(`includedServices.${index}.quantity`)}
          />
          <ActionIcon
            aria-label={removeLabel}
            color="red"
            disabled={disabled}
            mb={4}
            onClick={() => form.removeListItem("includedServices", index)}
            variant="subtle"
          >
            <IconTrash size={16} />
          </ActionIcon>
        </Group>
      ))}
      <Button
        disabled={disabled || included.length >= services.length}
        leftSection={<IconPlus size={16} />}
        onClick={() =>
          form.insertListItem(
            "includedServices",
            emptyIncludedService as Parameters<typeof form.insertListItem>[1],
          )
        }
        variant="light"
        w="fit-content"
      >
        {addLabel}
      </Button>
    </Stack>
  );
};

export default IncludedServicesEditor;
