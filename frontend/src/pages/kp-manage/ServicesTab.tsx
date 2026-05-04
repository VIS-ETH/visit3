import {
  ActionIcon,
  Button,
  Center,
  Group,
  Loader,
  NumberInput,
  Stack,
  Switch,
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
  getListServicesQueryKey,
  useCreateService,
  useDeleteService,
  useListServices,
  useUpdateService,
} from "../../orval/generated/kp/kp";
import { serviceSchema } from "../../schemas/kpSchema";
import { useTranslatedForm } from "../../utils/translator";
import ManageEntityModal from "./ManageEntityModal";
import {
  centsToCurrencyAmount,
  currencyAmountToCents,
} from "../../utils/price-utils";

export default function ServicesTab({ eventId }: { eventId: string }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data: services, isLoading } = useListServices(eventId);
  const [opened, { open, close }] = useDisclosure(false);
  const [editingServiceId, setEditingServiceId] = useState<string | null>(null);
  const form = useTranslatedForm<typeof serviceSchema>(serviceSchema, {
    initialValues: {
      name: "",
      description: "",
      price: 0,
      maxPerBooking: 1,
      maxTotal: 0,
      isActive: true,
    },
    validateInputOnChange: true,
  });

  const invalidate = () =>
    queryClient.invalidateQueries({
      queryKey: getListServicesQueryKey(eventId),
    });

  const resetForm = () => {
    form.setValues({
      name: "",
      description: "",
      price: 0,
      maxPerBooking: 1,
      maxTotal: 0,
      isActive: true,
    });
    form.resetDirty();
    form.clearErrors();
    setEditingServiceId(null);
  };

  const handleCloseModal = () => {
    close();
    resetForm();
  };

  const { mutate: create, isPending: isCreating } = useCreateService({
    mutation: {
      onSuccess: async () => {
        await invalidate();
        handleCloseModal();
        notifications.show({
          color: "green",
          message: t("kp.manage.service_created"),
        });
      },
    },
  });

  const { mutate: update, isPending: isUpdating } = useUpdateService({
    mutation: {
      onSuccess: async () => {
        await invalidate();
        if (editingServiceId !== null) {
          handleCloseModal();
        }
        notifications.show({
          color: "green",
          message: t("kp.manage.service_updated"),
        });
      },
    },
  });

  const { mutate: remove } = useDeleteService({
    mutation: {
      onSuccess: async () => {
        await invalidate();
        notifications.show({
          color: "green",
          message: t("kp.manage.service_deleted"),
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
  const isEditing = editingServiceId !== null;

  const openCreateModal = () => {
    resetForm();
    open();
  };

  const openEditModal = (service: NonNullable<typeof services>[number]) => {
    setEditingServiceId(service.id);
    form.setValues({
      name: service.name,
      description: service.description ?? "",
      price: centsToCurrencyAmount(service.price),
      maxPerBooking: service.max_quantity_per_booking,
      maxTotal: service.max_total_quantity,
      isActive: service.is_active,
    });
    form.resetDirty();
    form.clearErrors();
    open();
  };

  const handleSave = form.onSubmit((values) => {
    if (isEditing) {
      update({
        serviceId: editingServiceId,
        data: {
          name: values.name.trim(),
          description: values.description,
          price: currencyAmountToCents(values.price),
          max_quantity_per_booking: values.maxPerBooking,
          max_total_quantity: values.maxTotal,
          is_active: values.isActive,
        },
      });
      return;
    }
    create({
      eventId,
      data: {
        name: values.name.trim(),
        description: values.description,
        price: currencyAmountToCents(values.price),
        max_quantity_per_booking: values.maxPerBooking,
        max_total_quantity: values.maxTotal,
        is_active: values.isActive,
      },
    });
  });

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <Title order={4}>{t("kp.manage.services_title")}</Title>
        <Button
          leftSection={<IconPlus size={16} />}
          size="xs"
          onClick={openCreateModal}
        >
          {t("kp.manage.services_add")}
        </Button>
      </Group>

      <ManageEntityModal
        opened={opened}
        onClose={handleCloseModal}
        title={
          isEditing ? t("kp.manage.services_edit") : t("kp.manage.services_add")
        }
        isSaving={isSaving}
        isSubmitDisabled={!form.values.name.trim() || !form.isValid()}
        submitLabel={
          isEditing ? t("kp.manage.services_edit") : t("kp.manage.services_add")
        }
        onSubmit={handleSave}
      >
        <TextInput
          label={t("kp.manage.service_name")}
          disabled={isSaving}
          {...form.getInputProps("name")}
        />
        <Textarea
          label={t("kp.manage.service_description")}
          disabled={isSaving}
          {...form.getInputProps("description")}
        />
        <Group grow>
          <NumberInput
            label={t("kp.manage.service_price")}
            min={0}
            decimalScale={2}
            fixedDecimalScale
            disabled={isSaving}
            {...form.getInputProps("price")}
          />
          <NumberInput
            label={t("kp.manage.service_max_per_booking")}
            min={1}
            disabled={isSaving}
            {...form.getInputProps("maxPerBooking")}
          />
        </Group>
        <Group grow>
          <NumberInput
            label={t("kp.manage.service_max_total")}
            min={0}
            disabled={isSaving}
            {...form.getInputProps("maxTotal")}
          />
          <Switch
            label={t("kp.manage.service_active")}
            disabled={isSaving}
            mt="xl"
            {...form.getInputProps("isActive", { type: "checkbox" })}
          />
        </Group>
      </ManageEntityModal>

      {services && services.length > 0 ? (
        <Table highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>{t("kp.manage.service_name")}</Table.Th>
              <Table.Th>{t("kp.manage.service_price")}</Table.Th>
              <Table.Th>{t("kp.manage.service_max_per_booking")}</Table.Th>
              <Table.Th>{t("kp.manage.service_active")}</Table.Th>
              <Table.Th />
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {services.map((service) => (
              <Table.Tr key={service.id}>
                <Table.Td fw={500}>{service.name}</Table.Td>
                <Table.Td>{(service.price / 100).toFixed(2)}</Table.Td>
                <Table.Td>{service.max_quantity_per_booking}</Table.Td>
                <Table.Td>
                  <Switch
                    checked={service.is_active}
                    onChange={(e) =>
                      update({
                        serviceId: service.id,
                        data: { is_active: e.currentTarget.checked },
                      })
                    }
                    size="sm"
                  />
                </Table.Td>
                <Table.Td>
                  <ActionIcon
                    variant="subtle"
                    onClick={() => openEditModal(service)}
                    aria-label={t("kp.manage.services_edit")}
                  >
                    <IconEdit size={16} />
                  </ActionIcon>
                  <ActionIcon
                    color="red"
                    variant="subtle"
                    onClick={() => {
                      if (confirm(t("kp.manage.service_confirm_delete"))) {
                        remove({ serviceId: service.id });
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
        <Text c="dimmed">{t("kp.manage.services_empty")}</Text>
      )}
    </Stack>
  );
}
