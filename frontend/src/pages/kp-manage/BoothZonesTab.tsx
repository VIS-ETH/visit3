import {
  ActionIcon,
  Button,
  Center,
  ColorInput,
  Group,
  Loader,
  NumberInput,
  Stack,
  Table,
  Text,
  TextInput,
  Textarea,
  Title,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import { IconEdit, IconPlus, IconTrash } from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  getListBoothZonesQueryKey,
  useCreateBoothZone,
  useDeleteBoothZone,
  useListBoothZones,
  useUpdateBoothZone,
} from "../../orval/generated/kp/kp";
import { boothZoneSchema } from "../../schemas/kpSchema";
import { KpBoothZoneColorSwatch } from "../../components/KpBoothZoneColorSwatch";
import { useTranslatedForm } from "../../utils/translator";
import ManageEntityModal from "./ManageEntityModal";
import {
  centsToCurrencyAmount,
  currencyAmountToCents,
} from "../../utils/price-utils";

export default function BoothZonesTab({ eventId }: { eventId: string }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data: zones, isLoading } = useListBoothZones(eventId);
  const [opened, { open, close }] = useDisclosure(false);
  const [editingZoneId, setEditingZoneId] = useState<string | null>(null);
  const form = useTranslatedForm<typeof boothZoneSchema>(boothZoneSchema, {
    initialValues: {
      name: "",
      description: "",
      color: "#000000",
      capacity: 0,
      boothSize: 0,
      basePrice: 0,
    },
    validateInputOnChange: true,
  });

  const invalidate = () =>
    queryClient.invalidateQueries({
      queryKey: getListBoothZonesQueryKey(eventId),
    });

  const resetForm = () => {
    form.setValues({
      name: "",
      description: "",
      color: "#000000",
      capacity: 0,
      boothSize: 0,
      basePrice: 0,
    });
    form.resetDirty();
    form.clearErrors();
    setEditingZoneId(null);
  };

  const handleCloseModal = () => {
    close();
    resetForm();
  };

  const { mutate: create, isPending: isCreating } = useCreateBoothZone({
    mutation: {
      onSuccess: async () => {
        await invalidate();
        handleCloseModal();
        notifications.show({
          color: "green",
          message: t("kp.manage.zone_created"),
        });
      },
    },
  });

  const { mutate: update, isPending: isUpdating } = useUpdateBoothZone({
    mutation: {
      onSuccess: async () => {
        await invalidate();
        if (editingZoneId !== null) {
          handleCloseModal();
        }
        notifications.show({
          color: "green",
          message: t("kp.manage.zone_updated"),
        });
      },
    },
  });

  const { mutate: remove } = useDeleteBoothZone({
    mutation: {
      onSuccess: async () => {
        await invalidate();
        notifications.show({
          color: "green",
          message: t("kp.manage.zone_deleted"),
        });
      },
    },
  });

  if (isLoading) {
    return (
      <Center py="md">
        <Loader />
      </Center>
    );
  }

  const isSaving = isCreating || isUpdating;
  const isEditing = editingZoneId !== null;

  const openCreateModal = () => {
    resetForm();
    open();
  };

  const openEditModal = (zone: NonNullable<typeof zones>[number]) => {
    setEditingZoneId(zone.id);
    form.setValues({
      name: zone.name,
      description: zone.description ?? "",
      color: zone.color,
      capacity: zone.capacity,
      boothSize: zone.booth_size,
      basePrice: centsToCurrencyAmount(zone.base_price),
    });
    form.resetDirty();
    form.clearErrors();
    open();
  };

  const handleSave = form.onSubmit((values) => {
    if (isEditing) {
      update({
        boothZoneId: editingZoneId,
        data: {
          name: values.name.trim(),
          description: values.description,
          color: values.color,
          capacity: values.capacity,
          booth_size: values.boothSize,
          base_price: currencyAmountToCents(values.basePrice),
        },
      });
      return;
    }
    create({
      eventId,
      data: {
        name: values.name.trim(),
        description: values.description,
        color: values.color,
        capacity: values.capacity,
        booth_size: values.boothSize,
        base_price: currencyAmountToCents(values.basePrice),
      },
    });
  });

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <Title order={4}>{t("kp.manage.booth_zones_title")}</Title>
        <Button
          leftSection={<IconPlus size={16} />}
          size="xs"
          onClick={openCreateModal}
        >
          {t("kp.manage.booth_zones_add")}
        </Button>
      </Group>

      <ManageEntityModal
        opened={opened}
        onClose={handleCloseModal}
        title={
          isEditing
            ? t("kp.manage.booth_zones_edit")
            : t("kp.manage.booth_zones_add")
        }
        isSaving={isSaving}
        isSubmitDisabled={!form.values.name.trim() || !form.isValid()}
        submitLabel={
          isEditing
            ? t("kp.manage.booth_zones_edit")
            : t("kp.manage.booth_zones_add")
        }
        onSubmit={handleSave}
      >
        <TextInput
          label={t("kp.manage.zone_name")}
          disabled={isSaving}
          {...form.getInputProps("name")}
        />
        <Textarea
          label={t("kp.manage.zone_description")}
          disabled={isSaving}
          {...form.getInputProps("description")}
        />
        <ColorInput
          label={t("kp.manage.zone_color")}
          disabled={isSaving}
          {...form.getInputProps("color")}
        />
        <Group grow>
          <NumberInput
            label={t("kp.manage.zone_capacity")}
            min={0}
            disabled={isSaving}
            {...form.getInputProps("capacity")}
          />
          <NumberInput
            label={t("kp.manage.zone_booth_size")}
            min={0}
            decimalScale={2}
            disabled={isSaving}
            {...form.getInputProps("boothSize")}
          />
        </Group>
        <NumberInput
          label={t("kp.manage.zone_base_price")}
          min={0}
          decimalScale={2}
          fixedDecimalScale
          disabled={isSaving}
          {...form.getInputProps("basePrice")}
        />
      </ManageEntityModal>

      {zones && zones.length > 0 ? (
        <Table highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th />
              <Table.Th>{t("kp.manage.zone_name")}</Table.Th>
              <Table.Th>{t("kp.manage.zone_capacity")}</Table.Th>
              <Table.Th>{t("kp.manage.zone_booth_size")}</Table.Th>
              <Table.Th>{t("kp.manage.zone_base_price")}</Table.Th>
              <Table.Th />
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {zones.map((zone) => (
              <Table.Tr key={zone.id}>
                <Table.Td>
                  <KpBoothZoneColorSwatch color={zone.color} size={16} />
                </Table.Td>
                <Table.Td fw={500}>{zone.name}</Table.Td>
                <Table.Td>{zone.capacity}</Table.Td>
                <Table.Td>{zone.booth_size} m²</Table.Td>
                <Table.Td>{(zone.base_price / 100).toFixed(2)}</Table.Td>
                <Table.Td>
                  <ActionIcon
                    variant="subtle"
                    onClick={() => openEditModal(zone)}
                    aria-label={t("kp.manage.booth_zones_edit")}
                  >
                    <IconEdit size={16} />
                  </ActionIcon>
                  <ActionIcon
                    color="red"
                    variant="subtle"
                    onClick={() => {
                      if (confirm(t("kp.manage.zone_confirm_delete"))) {
                        remove({ boothZoneId: zone.id });
                      }
                    }}
                  >
                    <IconTrash size={16} />
                  </ActionIcon>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      ) : (
        <Text c="dimmed">{t("kp.manage.booth_zones_empty")}</Text>
      )}
    </Stack>
  );
}
