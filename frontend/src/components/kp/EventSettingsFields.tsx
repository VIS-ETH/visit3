import { NumberInput, SimpleGrid, Stack, Text, TextInput } from "@mantine/core";
import type { GetInputPropsReturnType } from "@mantine/form";
import { useTranslation } from "react-i18next";
import {
  MAX_VAT_RATE_PERCENT,
  type EventSettingsFormValues,
} from "../../schemas/eventSettingsSchema";

interface EventSettingsFieldsProps {
  disabled: boolean;
  getInputProps: (
    field: keyof EventSettingsFormValues,
  ) => GetInputPropsReturnType;
}

const EventSettingsFields = ({
  disabled,
  getInputProps,
}: EventSettingsFieldsProps) => {
  const { t } = useTranslation();

  return (
    <Stack gap="sm">
      <div>
        <Text fw={600}>{t("event_settings.title")}</Text>
        <Text c="dimmed" size="sm">
          {t("event_settings.description")}
        </Text>
      </div>
      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md" verticalSpacing="sm">
        <NumberInput
          label={t("event_settings.vat_rate")}
          description={t("event_settings.vat_rate_hint")}
          min={0}
          max={MAX_VAT_RATE_PERCENT}
          step={0.1}
          decimalScale={1}
          suffix="%"
          disabled={disabled}
          {...getInputProps("vatRatePercent")}
        />
        <NumberInput
          label={t("event_settings.reminder_days")}
          description={t("event_settings.reminder_days_hint")}
          min={0}
          allowDecimal={false}
          disabled={disabled}
          {...getInputProps("finalizationReminderDays")}
        />
        <TextInput
          label={t("event_settings.terms_url")}
          placeholder={t("event_settings.terms_url_placeholder")}
          disabled={disabled}
          {...getInputProps("termsUrl")}
        />
        <TextInput
          label={t("event_settings.notification_email")}
          description={t("event_settings.notification_email_hint")}
          placeholder={t("event_settings.notification_email_placeholder")}
          disabled={disabled}
          {...getInputProps("notificationEmail")}
        />
      </SimpleGrid>
    </Stack>
  );
};
export default EventSettingsFields;
