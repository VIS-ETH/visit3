import { Divider, SimpleGrid, Stack, Text, TextInput } from "@mantine/core";
import type { UseFormReturnType } from "@mantine/form";
import type { ChangeEvent } from "react";
import { useTranslation } from "react-i18next";
import { kpDateFieldNames } from "../../schemas/kpSchema";
import type { KpWithSettingsFormValues } from "../../schemas/eventSettingsSchema";
import EventSettingsFields from "./EventSettingsFields";

type EventForm = UseFormReturnType<KpWithSettingsFormValues>;

const dateFieldLabels: Record<(typeof kpDateFieldNames)[number], string> = {
  registrationOpen: "kp.dashboard.registration_open",
  registrationEnd: "kp.dashboard.registration_end",
  finalizationDeadline: "kp.dashboard.finalization_deadline",
  nametagsDeadline: "kp.dashboard.nametags_deadline",
  eventDate: "kp.dashboard.event_date",
};

interface EventFormFieldsProps {
  form: EventForm;
  disabled: boolean;
  showNotificationEmail?: boolean;
}

const EventFormFields = ({
  form,
  disabled,
  showNotificationEmail = true,
}: EventFormFieldsProps) => {
  const { t } = useTranslation();

  const getDateInputProps = (field: (typeof kpDateFieldNames)[number]) => {
    const inputProps = form.getInputProps(field);
    return {
      ...inputProps,
      onChange: (event: ChangeEvent<HTMLInputElement>) => {
        inputProps.onChange(event);
        for (const name of kpDateFieldNames) form.validateField(name);
      },
    };
  };

  return (
    <Stack gap="md">
      <Text c="dimmed" size="sm">
        {t("kp.dashboard.date_input_hint")}
      </Text>
      <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md" verticalSpacing="sm">
        <TextInput
          label={t("kp.dashboard.name")}
          placeholder={t("kp.dashboard.name_input_placeholder")}
          disabled={disabled}
          {...form.getInputProps("name")}
        />
        {kpDateFieldNames.map((field) => (
          <TextInput
            key={field}
            label={t(dateFieldLabels[field])}
            placeholder={t("kp.dashboard.date_input_placeholder")}
            disabled={disabled}
            {...getDateInputProps(field)}
          />
        ))}
      </SimpleGrid>
      <Divider />
      <EventSettingsFields
        disabled={disabled}
        showNotificationEmail={showNotificationEmail}
        getInputProps={(field) => form.getInputProps(field)}
      />
    </Stack>
  );
};

export default EventFormFields;
