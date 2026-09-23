import {
  ActionIcon,
  Alert,
  Anchor,
  Button,
  ColorInput,
  Divider,
  FileButton,
  Group,
  Image,
  NumberInput,
  Paper,
  Select,
  Stack,
  Text,
  TextInput,
  Textarea,
  Title,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import {
  IconAlertCircle,
  IconEdit,
  IconExternalLink,
  IconPlus,
  IconTrash,
  IconUpload,
} from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { getApiErrorCode } from "../api/errors";
import {
  getListBoothZonesQueryKey,
  type ListBoothZonesQueryResult,
  useCreateBoothZone,
  useDeleteBoothZone,
  useDeleteBoothZoneLayoutFile,
  useListBoothZones,
  useListServices,
  useUpdateBoothZone,
  useUploadBoothZoneLayoutFile,
} from "../orval/generated/kp/kp";
import { boothZoneSchema } from "../schemas/kpSchema";
import { KpBoothZoneColorSwatch } from "./KpBoothZoneColorSwatch";
import { useTranslatedForm } from "../utils/translator";
import ManageEntityModal from "./ManageEntityModal";
import {
  centsToCurrencyAmount,
  currencyAmountToCents,
} from "../utils/price-utils";
import {
  LAYOUT_UPLOAD_ACCEPT,
  isAllowedLayoutType,
  isPdfSource,
} from "../utils/upload-formats";
import DataTable, { type DataTableColumn } from "./DataTable";

type BoothZoneRow = ListBoothZonesQueryResult[number];

const emptyZoneValues = {
  name: "",
  description: "",
  color: "#000000",
  capacity: 0,
  boothSize: 0,
  basePrice: 0,
  layoutDescription: "",
  includedServices: [] as { serviceId: string; quantity: number }[],
};

const BoothZonesTab = ({ eventId }: { eventId: string }) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data: zones, isLoading } = useListBoothZones(eventId);
  const { data: services } = useListServices(eventId);
  const [opened, { open, close }] = useDisclosure(false);
  const [editingZoneId, setEditingZoneId] = useState<string | null>(null);
  const [saveErrorCode, setSaveErrorCode] = useState<string | null>(null);
  const [layoutFile, setLayoutFile] = useState<File | null>(null);
  const [isLayoutCleared, setIsLayoutCleared] = useState(false);
  const [layoutFileError, setLayoutFileError] = useState<string | null>(null);
  const form = useTranslatedForm<typeof boothZoneSchema>(boothZoneSchema, {
    initialValues: emptyZoneValues,
    validateInputOnChange: true,
  });

  const invalidate = () =>
    queryClient.invalidateQueries({
      queryKey: getListBoothZonesQueryKey(eventId),
    });

  const resetForm = () => {
    form.setValues(emptyZoneValues);
    form.resetDirty();
    form.clearErrors();
    setEditingZoneId(null);
    setSaveErrorCode(null);
    setLayoutFile(null);
    setIsLayoutCleared(false);
    setLayoutFileError(null);
  };

  const handleCloseModal = () => {
    close();
    resetForm();
  };

  const { mutateAsync: create, isPending: isCreating } = useCreateBoothZone();
  const { mutateAsync: update, isPending: isUpdating } = useUpdateBoothZone();
  const { mutateAsync: uploadLayout, isPending: isUploadingLayout } =
    useUploadBoothZoneLayoutFile();
  const { mutateAsync: deleteLayout, isPending: isDeletingLayout } =
    useDeleteBoothZoneLayoutFile();

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

  const isSaving =
    isCreating || isUpdating || isUploadingLayout || isDeletingLayout;
  const isEditing = editingZoneId !== null;
  const editingZone = zones?.find((zone) => zone.id === editingZoneId);
  const storedLayoutUrl = isLayoutCleared
    ? null
    : (editingZone?.layout_url ?? null);

  const openCreateModal = () => {
    resetForm();
    open();
  };

  const openEditModal = (zone: BoothZoneRow) => {
    setEditingZoneId(zone.id);
    setSaveErrorCode(null);
    setLayoutFile(null);
    setIsLayoutCleared(false);
    setLayoutFileError(null);
    form.setValues({
      name: zone.name,
      description: zone.description,
      color: zone.color,
      capacity: zone.capacity,
      boothSize: zone.booth_size,
      basePrice: centsToCurrencyAmount(zone.base_price),
      layoutDescription: zone.layout_description ?? "",
      includedServices: zone.included_services.map((included) => ({
        serviceId: included.service_id,
        quantity: included.included_quantity,
      })),
    });
    form.resetDirty();
    form.clearErrors();
    open();
  };

  const chooseLayoutFile = (file: File | null) => {
    if (file && !isAllowedLayoutType(file.type)) {
      setLayoutFileError(t("kp.manage.zone_layout_file_invalid"));
      return;
    }
    setLayoutFileError(null);
    setLayoutFile(file);
    if (file) setIsLayoutCleared(false);
  };

  const clearLayoutFile = () => {
    setLayoutFileError(null);
    setLayoutFile(null);
    setIsLayoutCleared(true);
  };

  const handleSave = form.onSubmit(async (values) => {
    setSaveErrorCode(null);
    const data = {
      name: values.name.trim(),
      description: values.description,
      color: values.color,
      capacity: values.capacity,
      booth_size: values.boothSize,
      base_price: currencyAmountToCents(values.basePrice),
      layout_description: values.layoutDescription.trim() || null,
      included_services: values.includedServices.map((included) => ({
        service_id: included.serviceId,
        included_quantity: included.quantity,
      })),
    };
    try {
      const saved =
        editingZoneId !== null
          ? await update({ boothZoneId: editingZoneId, data })
          : await create({ eventId, data });
      if (layoutFile) {
        await uploadLayout({
          boothZoneId: saved.id,
          data: { file: layoutFile },
        });
      } else if (isLayoutCleared && editingZone?.layout_url) {
        await deleteLayout({ boothZoneId: saved.id });
      }
    } catch (error) {
      setSaveErrorCode(getApiErrorCode(error) ?? "error.internal");
      return;
    }
    await invalidate();
    handleCloseModal();
    notifications.show({
      color: "green",
      message: isEditing
        ? t("kp.manage.zone_updated")
        : t("kp.manage.zone_created"),
    });
  });

  const serviceById = new Map(
    (services ?? []).map((service) => [service.id, service]),
  );

  const optionsForRow = (index: number) => {
    const takenIds = new Set(
      form.values.includedServices
        .filter((_, position) => position !== index)
        .map((included) => included.serviceId),
    );
    return (services ?? [])
      .filter((service) => !takenIds.has(service.id))
      .map((service) => ({ value: service.id, label: service.name }));
  };

  const columns: DataTableColumn<BoothZoneRow>[] = [
    {
      key: "color",
      header: "",
      render: (zone) => <KpBoothZoneColorSwatch color={zone.color} size={16} />,
      searchableValue: (zone) => zone.color,
      width: 40,
    },
    {
      key: "name",
      header: t("kp.manage.zone_name"),
      render: (zone) => zone.name,
      searchableValue: (zone) => zone.name,
    },
    {
      key: "capacity",
      header: t("kp.manage.zone_capacity"),
      render: (zone) => zone.capacity,
      searchableValue: (zone) => String(zone.capacity),
    },
    {
      key: "booth-size",
      header: t("kp.manage.zone_booth_size"),
      render: (zone) => `${zone.booth_size} m²`,
      searchableValue: (zone) => String(zone.booth_size),
    },
    {
      key: "base-price",
      header: t("kp.manage.zone_base_price"),
      render: (zone) => (zone.base_price / 100).toFixed(2),
      searchableValue: (zone) => (zone.base_price / 100).toFixed(2),
    },
    {
      key: "included-services",
      header: t("kp.manage.zone_included_services"),
      render: (zone) => zone.included_services.length,
      searchableValue: (zone) => String(zone.included_services.length),
      textAlign: "right",
      width: 150,
    },
    {
      key: "actions",
      header: "",
      render: (zone) => (
        <Group gap="xs">
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
            aria-label={t("kp.manage.zone_confirm_delete")}
            onClick={() => {
              if (confirm(t("kp.manage.zone_confirm_delete"))) {
                remove({ boothZoneId: zone.id });
              }
            }}
          >
            <IconTrash size={16} />
          </ActionIcon>
        </Group>
      ),
      width: 90,
    },
  ];

  return (
    <>
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

        <Divider label={t("kp.manage.zone_layout_title")} />
        <Textarea
          label={t("kp.manage.zone_layout_description")}
          disabled={isSaving}
          {...form.getInputProps("layoutDescription")}
        />
        <Stack gap="xs">
          <Text fw={500} size="sm">
            {t("kp.manage.zone_layout_file")}
          </Text>
          <Text c="dimmed" size="xs">
            {t("kp.manage.zone_layout_allowed_formats")}
          </Text>
          <Group align="center" gap="sm">
            <FileButton
              accept={LAYOUT_UPLOAD_ACCEPT}
              onChange={chooseLayoutFile}
            >
              {(props) => (
                <Button
                  {...props}
                  disabled={isSaving}
                  leftSection={<IconUpload size={16} />}
                  variant={
                    (layoutFile ?? storedLayoutUrl) ? "default" : "light"
                  }
                >
                  {(layoutFile ?? storedLayoutUrl)
                    ? t("kp.manage.zone_layout_replace")
                    : t("kp.manage.zone_layout_upload")}
                </Button>
              )}
            </FileButton>
            {(layoutFile ?? storedLayoutUrl) ? (
              <Button
                color="red"
                disabled={isSaving}
                leftSection={<IconTrash size={16} />}
                onClick={clearLayoutFile}
                variant="subtle"
              >
                {t("kp.manage.zone_layout_remove")}
              </Button>
            ) : null}
          </Group>
          {layoutFile ? (
            <Text size="sm">{layoutFile.name}</Text>
          ) : storedLayoutUrl ? (
            isPdfSource(storedLayoutUrl) ? (
              <Anchor
                href={storedLayoutUrl}
                target="_blank"
                rel="noopener noreferrer"
              >
                <Group gap={6} wrap="nowrap">
                  <IconExternalLink size={16} />
                  <Text size="sm">{t("kp.manage.zone_layout_open_pdf")}</Text>
                </Group>
              </Anchor>
            ) : (
              <Image
                alt={t("kp.manage.zone_layout_preview_alt")}
                fit="contain"
                mah={200}
                radius="sm"
                src={storedLayoutUrl}
              />
            )
          ) : (
            <Text c="dimmed" size="sm">
              {t("kp.manage.zone_layout_none")}
            </Text>
          )}
          {layoutFileError !== null ? (
            <Text c="red" size="sm">
              {layoutFileError}
            </Text>
          ) : null}
        </Stack>

        <Divider label={t("kp.manage.zone_included_services")} />
        <Stack gap="sm">
          {form.values.includedServices.length === 0 ? (
            <Text c="dimmed" size="sm">
              {t("kp.manage.zone_included_empty")}
            </Text>
          ) : null}
          {form.values.includedServices.map((included, index) => (
            <Group align="flex-end" gap="xs" key={index} wrap="nowrap">
              <Select
                data={optionsForRow(index)}
                disabled={isSaving}
                flex={1}
                label={t("kp.manage.zone_included_service")}
                searchable
                {...form.getInputProps(`includedServices.${index}.serviceId`)}
              />
              <NumberInput
                allowDecimal={false}
                clampBehavior="strict"
                disabled={isSaving}
                label={t("kp.manage.zone_included_quantity")}
                min={1}
                max={
                  serviceById.get(included.serviceId)
                    ?.max_quantity_per_booking ?? 999
                }
                w={140}
                {...form.getInputProps(`includedServices.${index}.quantity`)}
              />
              <ActionIcon
                aria-label={t("kp.manage.zone_included_remove")}
                color="red"
                disabled={isSaving}
                mb={4}
                onClick={() => form.removeListItem("includedServices", index)}
                variant="subtle"
              >
                <IconTrash size={16} />
              </ActionIcon>
            </Group>
          ))}
          <Button
            disabled={
              isSaving ||
              form.values.includedServices.length >= (services?.length ?? 0)
            }
            leftSection={<IconPlus size={16} />}
            onClick={() =>
              form.insertListItem("includedServices", {
                serviceId: "",
                quantity: 1,
              })
            }
            variant="light"
          >
            {t("kp.manage.zone_included_add")}
          </Button>
        </Stack>
        {saveErrorCode !== null ? (
          <Alert color="red" icon={<IconAlertCircle />}>
            {t(saveErrorCode)}
          </Alert>
        ) : null}
      </ManageEntityModal>

      <Paper withBorder p="lg" radius="md">
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

          <DataTable
            columns={columns}
            data={zones}
            emptyLabel={t("kp.manage.booth_zones_empty")}
            getRowKey={(zone) => zone.id}
            isLoading={isLoading}
          />
        </Stack>
      </Paper>
    </>
  );
};
export default BoothZonesTab;
