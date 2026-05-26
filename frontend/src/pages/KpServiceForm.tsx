import {
  ActionIcon,
  Alert,
  Button,
  Center,
  Divider,
  Group,
  Loader,
  NumberInput,
  Paper,
  Select,
  Stack,
  Switch,
  Text,
  TextInput,
  Textarea,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconAlertCircle, IconPlus, IconTrash } from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router";
import BackButton from "../components/BackButton";
import ImageUploadInput from "../components/ImageUploadInput";
import { KpEventServiceRequirementType } from "../orval/generated/fastAPI.schemas";
import {
  getListServicesQueryKey,
  useCreateService,
  useDeleteServiceImage,
  useListServices,
  useUpdateService,
  useUploadServiceImage,
} from "../orval/generated/kp/kp";
import { serviceSchema } from "../schemas/kpSchema";
import {
  centsToCurrencyAmount,
  currencyAmountToCents,
} from "../utils/price-utils";
import { useTranslatedForm } from "../utils/translator";

type ServiceRequirementFormValue = {
  id?: string;
  type: string;
  name: string;
  description: string;
  order: number;
};

const emptyRequirement = (): ServiceRequirementFormValue => ({
  type: KpEventServiceRequirementType.file,
  name: "",
  description: "",
  order: 100,
});

const emptyServiceFormValues = {
  name: "",
  description: "",
  imageUrl: "",
  price: 0,
  maxPerBooking: 1,
  maxTotal: 0,
  isActive: true,
  requirements: [],
};

const KpServiceForm = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { id: eventId, serviceId } = useParams<{
    id: string;
    serviceId?: string;
  }>();
  const isEditing = Boolean(serviceId);
  const [serviceImageFile, setServiceImageFile] = useState<File | null>(null);
  const [serviceImageCleared, setServiceImageCleared] = useState(false);
  const servicesPath = `/kp/${eventId}?tab=services`;
  const { data: services, isLoading } = useListServices(eventId ?? "");
  const service = services?.find((item) => item.id === serviceId);

  const form = useTranslatedForm<typeof serviceSchema>(serviceSchema, {
    initialValues: emptyServiceFormValues,
    validateInputOnChange: true,
  });

  const invalidate = () =>
    queryClient.invalidateQueries({
      queryKey: getListServicesQueryKey(eventId ?? ""),
    });

  const { mutateAsync: create, isPending: isCreating } = useCreateService();

  const { mutateAsync: update, isPending: isUpdating } = useUpdateService();
  const { mutateAsync: uploadServiceImage, isPending: isUploadingImage } =
    useUploadServiceImage();
  const { mutateAsync: deleteServiceImage, isPending: isDeletingImage } =
    useDeleteServiceImage();

  const isSaving =
    isCreating || isUpdating || isUploadingImage || isDeletingImage;

  useEffect(() => {
    if (!service) return;
    form.setValues({
      name: service.name,
      description: service.description,
      imageUrl: service.image_url ?? "",
      price: centsToCurrencyAmount(service.price),
      maxPerBooking: service.max_quantity_per_booking,
      maxTotal: service.max_total_quantity,
      isActive: service.is_active,
      requirements: service.requirements.map((requirement) => ({
        id: requirement.id,
        type: requirement.type,
        name: requirement.name,
        description: requirement.description,
        order: requirement.order,
      })),
    });
    form.resetDirty();
    form.clearErrors();
    setServiceImageFile(null);
    setServiceImageCleared(false);
    // Only initialize when the target service changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [service?.id]);

  const requirementTypeOptions = [
    {
      value: KpEventServiceRequirementType.text,
      label: t("kp.manage.requirement_type_text"),
    },
    {
      value: KpEventServiceRequirementType.file,
      label: t("kp.manage.requirement_type_file"),
    },
    {
      value: KpEventServiceRequirementType.image,
      label: t("kp.manage.requirement_type_image"),
    },
    {
      value: KpEventServiceRequirementType.pdf,
      label: t("kp.manage.requirement_type_pdf"),
    },
    {
      value: KpEventServiceRequirementType.video,
      label: t("kp.manage.requirement_type_video"),
    },
  ];

  const handleSave = form.onSubmit(async (values) => {
    if (!eventId) return;
    const requirements = values.requirements.map((requirement) => ({
      ...requirement,
      type: requirement.type as KpEventServiceRequirementType,
    }));
    const data = {
      name: values.name.trim(),
      description: values.description,
      price: currencyAmountToCents(values.price),
      max_quantity_per_booking: values.maxPerBooking,
      max_total_quantity: values.maxTotal,
      is_active: values.isActive,
      requirements,
    };

    const saveImage = async (nextServiceId: string) => {
      if (serviceImageFile) {
        await uploadServiceImage({
          serviceId: nextServiceId,
          data: { file: serviceImageFile },
        });
        return;
      }
      if (serviceImageCleared && service?.image_url) {
        await deleteServiceImage({ serviceId: nextServiceId });
      }
    };

    if (serviceId) {
      const updated = await update({ serviceId, data });
      await saveImage(updated.id);
      await invalidate();
      notifications.show({
        color: "green",
        message: t("kp.manage.service_updated"),
      });
      navigate(servicesPath);
      return;
    }
    const created = await create({ eventId, data });
    await saveImage(created.id);
    await invalidate();
    notifications.show({
      color: "green",
      message: t("kp.manage.service_created"),
    });
    navigate(servicesPath);
  });

  if (!eventId) {
    return (
      <Stack gap="md">
        <BackButton to="/kp" />
        <Alert icon={<IconAlertCircle />} color="red">
          {t("kp.manage.not_found")}
        </Alert>
      </Stack>
    );
  }

  if (isEditing && isLoading) {
    return (
      <Stack gap="md">
        <BackButton to={servicesPath} />
        <Center py="xl">
          <Loader />
        </Center>
      </Stack>
    );
  }

  if (isEditing && !service) {
    return (
      <Stack gap="md">
        <BackButton to={servicesPath} />
        <Alert icon={<IconAlertCircle />} color="red">
          {t("kp.manage.service_not_found")}
        </Alert>
      </Stack>
    );
  }

  return (
    <Stack gap="md">
      <BackButton to={servicesPath} />
      <Group justify="space-between" align="flex-start">
        <Title order={2}>
          {isEditing ? t("kp.manage.services_edit") : t("kp.manage.services_add")}
        </Title>
      </Group>

      <form id="kp-service-form" onSubmit={handleSave}>
        <Paper withBorder p="lg" radius="md">
          <Stack gap="md">
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
            <ImageUploadInput
              label={t("kp.manage.service_image")}
              previewAlt={t("kp.manage.service_image_preview")}
              uploadLabel={t("kp.manage.service_image_upload")}
              replaceLabel={t("kp.manage.service_image_replace")}
              previewLabel={t("kp.manage.service_image_open_preview")}
              clearLabel={t("kp.manage.service_image_clear")}
              currentFileLabel={t("kp.manage.service_image_current_file")}
              invalidFileMessage={t("kp.manage.service_image_file_invalid")}
              disabled={isSaving}
              value={form.values.imageUrl}
              onChange={(value) => {
                form.setFieldValue("imageUrl", value);
                setServiceImageCleared(!value.trim());
              }}
              onFileChange={(file) => {
                setServiceImageFile(file);
                if (file) setServiceImageCleared(false);
              }}
              error={form.errors.imageUrl}
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

            <Divider label={t("kp.manage.service_requirements")} />
            <Stack gap="md">
              {form.values.requirements.length === 0 ? (
                <Text c="dimmed" size="sm">
                  {t("kp.manage.requirements_empty")}
                </Text>
              ) : null}
              {form.values.requirements.map((requirement, index) => (
                <Paper withBorder p="sm" radius="md" key={requirement.id ?? index}>
                  <Stack gap="sm">
                    <Group justify="space-between" align="center">
                      <Text fw={600} size="sm">
                        {t("kp.manage.requirement_title", {
                          number: index + 1,
                        })}
                      </Text>
                      <ActionIcon
                        aria-label={t("kp.manage.requirement_remove")}
                        color="red"
                        disabled={isSaving}
                        onClick={() => form.removeListItem("requirements", index)}
                        size="sm"
                        variant="subtle"
                      >
                        <IconTrash size={16} />
                      </ActionIcon>
                    </Group>
                    <Group grow>
                      <TextInput
                        label={t("kp.manage.requirement_name")}
                        disabled={isSaving}
                        {...form.getInputProps(`requirements.${index}.name`)}
                      />
                      <Select
                        allowDeselect={false}
                        data={requirementTypeOptions}
                        label={t("kp.manage.requirement_type")}
                        disabled={isSaving}
                        {...form.getInputProps(`requirements.${index}.type`)}
                      />
                      <NumberInput
                        label={t("kp.manage.requirement_order")}
                        min={0}
                        disabled={isSaving}
                        {...form.getInputProps(`requirements.${index}.order`)}
                      />
                    </Group>
                    <Textarea
                      label={t("kp.manage.requirement_description")}
                      disabled={isSaving}
                      {...form.getInputProps(
                        `requirements.${index}.description`,
                      )}
                    />
                  </Stack>
                </Paper>
              ))}
              <Button
                leftSection={<IconPlus size={16} />}
                onClick={() =>
                  form.insertListItem("requirements", emptyRequirement())
                }
                variant="light"
              >
                {t("kp.manage.requirement_add")}
              </Button>
            </Stack>
            <Group justify="flex-end" mt="sm">
              <Button
                component={Link}
                to={servicesPath}
                variant="default"
                disabled={isSaving}
              >
                {t("common.cancel")}
              </Button>
              <Button
                type="submit"
                loading={isSaving}
                disabled={!form.values.name.trim() || !form.isValid()}
              >
                {t("kp.manage.save")}
              </Button>
            </Group>
          </Stack>
        </Paper>
      </form>
    </Stack>
  );
};

export default KpServiceForm;
