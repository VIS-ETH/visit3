import {
  ActionIcon,
  Button,
  Group,
  NumberInput,
  Paper,
  Select,
  Stack,
  Text,
  TextInput,
  Textarea,
} from "@mantine/core";
import type { UseFormReturnType } from "@mantine/form";
import { IconPlus, IconTrash } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import { KpEventServiceRequirementType } from "../../orval/generated/fastAPI.schemas";
import type { ServiceFormValues } from "./service-form-values";

const REQUIREMENT_TYPE_LABEL_KEYS: Record<
  KpEventServiceRequirementType,
  string
> = {
  [KpEventServiceRequirementType.text]: "kp.manage.requirement_type_text",
  [KpEventServiceRequirementType.file]: "kp.manage.requirement_type_file",
  [KpEventServiceRequirementType.image]: "kp.manage.requirement_type_image",
  [KpEventServiceRequirementType.pdf]: "kp.manage.requirement_type_pdf",
  [KpEventServiceRequirementType.video]: "kp.manage.requirement_type_video",
};

const emptyRequirement = () => ({
  type: KpEventServiceRequirementType.file,
  name: "",
  description: "",
  order: 100,
});

const ServiceRequirementsEditor = ({
  form,
  disabled,
}: {
  form: UseFormReturnType<ServiceFormValues>;
  disabled: boolean;
}) => {
  const { t } = useTranslation();
  const typeOptions = Object.values(KpEventServiceRequirementType).map(
    (type) => ({ value: type, label: t(REQUIREMENT_TYPE_LABEL_KEYS[type]) }),
  );
  const { requirements } = form.values;

  return (
    <Stack gap="md">
      {requirements.length === 0 ? (
        <Text c="dimmed" size="sm">
          {t("kp.manage.requirements_empty")}
        </Text>
      ) : null}
      {requirements.map((requirement, index) => (
        <Paper withBorder p="sm" radius="md" key={requirement.id ?? index}>
          <Stack gap="sm">
            <Group justify="space-between" align="center">
              <Text fw={600} size="sm">
                {t("kp.manage.requirement_title", { number: index + 1 })}
              </Text>
              <ActionIcon
                aria-label={t("kp.manage.requirement_remove")}
                color="red"
                disabled={disabled}
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
                disabled={disabled}
                {...form.getInputProps(`requirements.${index}.name`)}
              />
              <Select
                allowDeselect={false}
                data={typeOptions}
                label={t("kp.manage.requirement_type")}
                disabled={disabled}
                {...form.getInputProps(`requirements.${index}.type`)}
              />
              <NumberInput
                allowDecimal={false}
                label={t("kp.manage.requirement_order")}
                min={0}
                disabled={disabled}
                {...form.getInputProps(`requirements.${index}.order`)}
              />
            </Group>
            <Textarea
              label={t("kp.manage.requirement_description")}
              disabled={disabled}
              {...form.getInputProps(`requirements.${index}.description`)}
            />
          </Stack>
        </Paper>
      ))}
      <Button
        disabled={disabled}
        leftSection={<IconPlus size={16} />}
        onClick={() => form.insertListItem("requirements", emptyRequirement())}
        variant="light"
      >
        {t("kp.manage.requirement_add")}
      </Button>
    </Stack>
  );
};

export default ServiceRequirementsEditor;
