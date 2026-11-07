import {
  Group,
  NumberInput,
  SegmentedControl,
  Stack,
  Switch,
  Text,
  TextInput,
  Textarea,
} from "@mantine/core";
import type { UseFormReturnType } from "@mantine/form";
import { useTranslation } from "react-i18next";
import { KpServiceCategory } from "../../orval/generated/fastAPI.schemas";
import ImageUploadInput from "../ImageUploadInput";
import type { ServiceFormValues } from "./service-form-values";

const ServiceDetailsFields = ({
  form,
  disabled,
  onImageUrlChange,
  onImageFileChange,
}: {
  form: UseFormReturnType<ServiceFormValues>;
  disabled: boolean;
  onImageUrlChange: (url: string) => void;
  onImageFileChange: (file: File | null) => void;
}) => {
  const { t } = useTranslation();
  const categoryOptions = [
    {
      value: KpServiceCategory.SERVICE,
      label: t("kp.manage.service_category_service"),
    },
    {
      value: KpServiceCategory.BOOTH_ELEMENT,
      label: t("kp.manage.service_category_booth_element"),
    },
  ];

  return (
    <>
      <TextInput
        label={t("kp.manage.service_name")}
        disabled={disabled}
        {...form.getInputProps("name")}
      />
      <Textarea
        label={t("kp.manage.service_description")}
        disabled={disabled}
        {...form.getInputProps("description")}
      />
      <Stack gap={4}>
        <Text fw={500} size="sm">
          {t("kp.manage.service_category")}
        </Text>
        <SegmentedControl
          data={categoryOptions}
          disabled={disabled}
          fullWidth
          {...form.getInputProps("category")}
        />
      </Stack>
      <TextInput
        label={t("kp.manage.service_unit_label")}
        description={t("kp.manage.service_unit_label_description")}
        disabled={disabled}
        {...form.getInputProps("unitLabel")}
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
        allowedFormatsLabel={t("kp.manage.service_image_allowed_formats")}
        disabled={disabled}
        value={form.values.imageUrl}
        onChange={(value) => {
          form.setFieldValue("imageUrl", value);
          onImageUrlChange(value);
        }}
        onFileChange={onImageFileChange}
        error={form.errors.imageUrl}
      />
      <Group grow>
        <NumberInput
          label={t("kp.manage.service_price")}
          min={0}
          decimalScale={2}
          fixedDecimalScale
          disabled={disabled}
          {...form.getInputProps("price")}
        />
        <NumberInput
          allowDecimal={false}
          label={t("kp.manage.service_max_per_booking")}
          min={1}
          disabled={disabled}
          {...form.getInputProps("maxPerBooking")}
        />
      </Group>
      <Group grow>
        <NumberInput
          allowDecimal={false}
          label={t("kp.manage.service_max_total")}
          min={0}
          disabled={disabled}
          {...form.getInputProps("maxTotal")}
        />
        <Switch
          label={t("kp.manage.service_active")}
          disabled={disabled}
          mt="xl"
          {...form.getInputProps("isActive", { type: "checkbox" })}
        />
      </Group>
    </>
  );
};

export default ServiceDetailsFields;
